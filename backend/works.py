"""作品保存、查询、更新、删除：资源版本化持久化 + 归属校验 + 并发保护。

- 作品资源按 `works/<work_id>/<asset_version>/` 版本目录存储，永不原地覆盖。
- 保存时在 `.staging/` 中构建新版本目录，渲染预览、校验后原子改名落盘，再用 CAS 更新数据库。
- 旧版本在 CAS 成功后写入 retired_at 标记，由 GC 在超过保留期后清理（不立即删除）。
- 用户身份一律来自 Session（get_current_user），所有读写校验归属，跨用户一律 404。
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth import get_current_user
from db import get_connection, GENERATED_DIR, WORKS_DIR
from poster_design_source import STATIC_DIR as POSTER_DESIGN_STATIC_DIR

STATIC_PREFIX = "/works-static"
STAGING_DIR = WORKS_DIR / ".staging"
RETENTION_SECONDS = 24 * 60 * 60
RETIRED_AT_FILENAME = "retired_at"

router = APIRouter(prefix="/api/works", tags=["works"])


class StaleResourceError(ValueError):
    """资源 URL 引用的版本不是当前版本（并发更新或客户端过期）。"""


# ── 并发保护 ─────────────────────────────────────────────
_locks_guard = threading.Lock()
_work_locks: dict[str, threading.Lock] = {}

_staging_guard = threading.Lock()
_active_staging: set[Path] = set()


def _lock_for(work_id: str) -> threading.Lock:
    with _locks_guard:
        lock = _work_locks.get(work_id)
        if lock is None:
            lock = threading.Lock()
            _work_locks[work_id] = lock
        return lock


def _register_staging(path: Path) -> None:
    with _staging_guard:
        _active_staging.add(path)


def _unregister_staging(path: Path) -> None:
    with _staging_guard:
        _active_staging.discard(path)


# ── 请求模型 ─────────────────────────────────────────────
class SaveRequest(BaseModel):
    title: str | None = None
    style: str | None = None
    # 用 alias 避免字段名 "copy" 遮蔽 BaseModel.copy
    copy_data: dict[str, Any] | None = Field(default=None, alias="copy")
    document: dict[str, Any]


# ── URL 校验与资源解析 ───────────────────────────────────
_ALLOWED_PREFIXES = ("/generated/", "/poster-design-static/", "/works-static/")
_WORK_ID_RE = re.compile(r"[a-f0-9]{32}")


def _classify_url(url: str) -> tuple[str, str]:
    """校验并解析资源 URL，返回 (前缀, 相对路径)。严格防穿越/非法编码。"""
    if not isinstance(url, str) or not url or not url.startswith("/"):
        raise ValueError("资源 URL 必须是以 / 开头的绝对路径。")
    if any(ch in url for ch in ("?", "#", "\\")):
        raise ValueError("资源 URL 含非法字符（query/fragment/反斜杠）。")
    decoded = unquote(url)
    if "%" in decoded:
        raise ValueError("资源 URL 含二次编码。")
    if any(ch in decoded for ch in ("?", "#", "\\")):
        raise ValueError("资源 URL 含非法字符。")
    segments = [seg for seg in decoded.split("/") if seg]
    if any(seg in (".", "..") for seg in segments):
        raise ValueError("资源 URL 含路径穿越。")
    for prefix in _ALLOWED_PREFIXES:
        if decoded.startswith(prefix):
            relative = decoded[len(prefix):]
            if not relative:
                raise ValueError("资源 URL 缺少路径。")
            return prefix, relative
    raise ValueError("资源 URL 不在允许范围内（仅 generated/poster-design-static/works-static）。")


def _source_file(prefix: str, relative: str) -> Path:
    """把已校验的 URL 解析为磁盘源文件，并确保不越出资源根目录。"""
    base = {
        "/generated/": GENERATED_DIR,
        "/poster-design-static/": POSTER_DESIGN_STATIC_DIR,
        "/works-static/": WORKS_DIR,
    }[prefix]
    target = (base / relative).resolve()
    root = base.resolve()
    if root != target and root not in target.parents:
        raise ValueError("资源路径越出根目录。")
    return target


def _works_url(work_id: str, version: str, filename: str) -> str:
    return f"{STATIC_PREFIX}/{work_id}/{version}/{filename}"


def _collect_asset_urls(document: dict[str, Any]) -> list[str]:
    """收集 document 中所有引用的图片资源 URL（去重保序）。"""
    urls: list[str] = []
    canvas = document.get("canvas") or {}
    bg = canvas.get("backgroundImage")
    if isinstance(bg, str) and bg:
        urls.append(bg)
    for element in document.get("elements", []):
        if not isinstance(element, dict):
            continue
        if element.get("type") == "image" and isinstance(element.get("src"), str) and element["src"]:
            urls.append(element["src"])
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result


def _validate_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise HTTPException(400, "document 必须是 JSON 对象。")
    canvas = document.get("canvas")
    if not isinstance(canvas, dict) or not canvas.get("width") or not canvas.get("height"):
        raise HTTPException(400, "document 缺少画布宽高。")
    if not isinstance(document.get("elements"), list):
        raise HTTPException(400, "document.elements 必须是数组。")
    return document


def _default_title(document: dict[str, Any]) -> str:
    return (
        str(document.get("productName") or document.get("name") or "").strip()
        or "未命名作品"
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _render_preview(document: dict[str, Any], works_root: Path, version_dir: Path) -> None:
    # 惰性导入：api.py 在导入本模块时尚未完成加载，_render 只能在调用时解析。
    from api import _render

    _render(document, works_root=works_root).save(version_dir / "preview.jpg", quality=90)


def _build_staging(
    work_id: str,
    new_version: str,
    old_version: str | None,
    document: dict[str, Any],
) -> tuple[Path, Path, dict[str, Any]]:
    """在 .staging 中构建新版本目录，返回 (staging_parent, version_dir, 改写后的 document)。"""
    staging_parent = STAGING_DIR / f"{work_id}.{new_version}.{secrets.token_hex(4)}"
    version_dir = staging_parent / work_id / new_version
    version_dir.mkdir(parents=True, exist_ok=False)
    _register_staging(staging_parent)
    try:
        rewritten = json.loads(json.dumps(document))
        counter = 0
        name_map: dict[str, str] = {}
        for url in _collect_asset_urls(rewritten):
            prefix, relative = _classify_url(url)
            if prefix == "/works-static/":
                # PUT 更新：只允许引用本作品、且版本等于当前数据库版本的资源。
                parts = relative.split("/")
                if len(parts) < 2 or parts[0] != work_id:
                    raise ValueError("资源 URL 引用了其他作品。")
                if old_version is None or parts[1] != old_version:
                    raise StaleResourceError("资源 URL 的版本不是当前版本。")
            src = _source_file(prefix, relative)
            if not src.is_file():
                raise ValueError(f"资源文件不存在：{url}")
            if url not in name_map:
                new_name = f"asset_{counter}{src.suffix or '.png'}"
                name_map[url] = new_name
                counter += 1
                shutil.copy2(src, version_dir / new_name)
        rewritten["canvas"] = dict(rewritten.get("canvas") or {})
        bg = rewritten["canvas"].get("backgroundImage")
        if isinstance(bg, str) and bg in name_map:
            rewritten["canvas"]["backgroundImage"] = _works_url(work_id, new_version, name_map[bg])
        for element in rewritten.get("elements", []):
            if not isinstance(element, dict):
                continue
            if element.get("type") == "image" and element.get("src") in name_map:
                element["src"] = _works_url(work_id, new_version, name_map[element["src"]])
        _render_preview(rewritten, staging_parent, version_dir)
        return staging_parent, version_dir, rewritten
    except Exception:
        _unregister_staging(staging_parent)
        shutil.rmtree(staging_parent, ignore_errors=True)
        raise


# ── 旧版本标记与 GC ─────────────────────────────────────
def _mark_retired(version_dir: Path) -> None:
    marker = version_dir / RETIRED_AT_FILENAME
    tmp = marker.with_suffix(".tmp")
    tmp.write_text(str(time.time()), encoding="utf-8")
    os.replace(tmp, marker)  # 原子写


def _sweep_gc() -> None:
    """机会式清理（失败绝不影响正常请求）。"""
    try:
        _sweep_versions()
    except Exception:
        pass
    try:
        _sweep_staging()
    except Exception:
        pass


def _sweep_versions() -> None:
    if not WORKS_DIR.is_dir():
        return
    now = time.time()
    for work_dir in WORKS_DIR.iterdir():
        if not work_dir.is_dir() or work_dir.name.startswith("."):
            continue
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT asset_version FROM works WHERE id = ?", (work_dir.name,)
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            continue  # 无 DB 记录的作品目录：保守保留
        current = row["asset_version"]
        for version_dir in work_dir.iterdir():
            if not version_dir.is_dir() or version_dir.name == current:
                continue
            marker = version_dir / RETIRED_AT_FILENAME
            if not marker.is_file():
                continue  # 无 retired_at → 保留（安全策略）
            try:
                retired = float(marker.read_text(encoding="utf-8").strip())
            except (OSError, ValueError):
                continue
            if now - retired > RETENTION_SECONDS:
                shutil.rmtree(version_dir, ignore_errors=True)


def _sweep_staging() -> None:
    if not STAGING_DIR.is_dir():
        return
    now = time.time()
    for entry in STAGING_DIR.iterdir():
        with _staging_guard:
            active = entry in _active_staging
        if active:
            continue  # 活跃保存任务，绝不清理
        try:
            if entry.is_dir() and (now - entry.stat().st_mtime) > RETENTION_SECONDS:
                shutil.rmtree(entry, ignore_errors=True)
        except OSError:
            continue


# ── DB 写入 ──────────────────────────────────────────────
def _insert_work(connection, work_id, user_id, title, meta, document_json, preview_url, version, now):
    connection.execute(
        "INSERT INTO works (id, user_id, title, meta_json, document_json, preview_url, asset_version, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (work_id, user_id, title, meta, document_json, preview_url, version, now, now),
    )
    connection.commit()


def _update_work_cas(connection, work_id, user_id, old_version, title, meta, document_json, preview_url, version, now) -> int:
    cursor = connection.execute(
        "UPDATE works SET document_json=?, preview_url=?, asset_version=?, title=?, meta_json=?, updated_at=? "
        "WHERE id=? AND user_id=? AND asset_version=?",
        (document_json, preview_url, version, title, meta, now, work_id, user_id, old_version),
    )
    connection.commit()
    return cursor.rowcount


def _commit_version(staging_parent: Path, version_dir: Path, work_id: str, version: str) -> Path:
    """把 staging 中的版本目录原子改名到最终位置，返回 target_dir。"""
    target_dir = WORKS_DIR / work_id / version
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    os.replace(version_dir, target_dir)
    return target_dir


def _cleanup_staging_parent(staging_parent: Path) -> None:
    _unregister_staging(staging_parent)
    shutil.rmtree(staging_parent, ignore_errors=True)


# ── 接口 ─────────────────────────────────────────────────
@router.post("", status_code=201)
def create_work(payload: SaveRequest, user: dict = Depends(get_current_user)):
    _sweep_gc()
    document = _validate_document(payload.document)
    user_id = user["id"]
    work_id = uuid.uuid4().hex
    new_version = secrets.token_hex(16)
    title = (payload.title or "").strip() or _default_title(document)
    meta = json.dumps(
        {"style": payload.style, "copy": payload.copy_data or {}, "productName": document.get("productName")},
        ensure_ascii=False,
    )

    try:
        staging_parent, version_dir, rewritten = _build_staging(work_id, new_version, None, document)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(400, f"保存失败：{error}")

    try:
        target_dir = _commit_version(staging_parent, version_dir, work_id, new_version)
    except OSError as error:
        _cleanup_staging_parent(staging_parent)
        raise HTTPException(500, f"作品目录落盘失败：{error}")
    _cleanup_staging_parent(staging_parent)

    now = _now_iso()
    preview_url = _works_url(work_id, new_version, "preview.jpg")
    connection = get_connection()
    try:
        _insert_work(
            connection, work_id, user_id, title, meta,
            json.dumps(rewritten, ensure_ascii=False), preview_url, new_version, now,
        )
    except Exception as error:
        shutil.rmtree(target_dir, ignore_errors=True)  # 补偿：清理已落盘但未入库的新版本
        raise HTTPException(500, f"写入数据库失败：{error}")
    finally:
        connection.close()

    return {"id": work_id, "title": title, "previewUrl": preview_url, "createdAt": now, "updatedAt": now}


@router.get("")
def list_works(user: dict = Depends(get_current_user)):
    _sweep_gc()
    connection = get_connection()
    try:
        rows = connection.execute(
            "SELECT id, title, preview_url, created_at, updated_at FROM works "
            "WHERE user_id = ? ORDER BY updated_at DESC",
            (user["id"],),
        ).fetchall()
    finally:
        connection.close()
    return {
        "works": [
            {
                "id": row["id"],
                "title": row["title"],
                "previewUrl": row["preview_url"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"],
            }
            for row in rows
        ]
    }


@router.get("/{work_id}")
def get_work(work_id: str, user: dict = Depends(get_current_user)):
    if not _WORK_ID_RE.fullmatch(work_id):
        raise HTTPException(404, "作品不存在。")
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT id, title, meta_json, document_json, preview_url, created_at, updated_at "
            "FROM works WHERE id = ? AND user_id = ?",
            (work_id, user["id"]),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        raise HTTPException(404, "作品不存在。")
    return {
        "id": row["id"],
        "title": row["title"],
        "meta": json.loads(row["meta_json"] or "{}"),
        "document": json.loads(row["document_json"]),
        "previewUrl": row["preview_url"],
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


@router.put("/{work_id}")
def update_work(work_id: str, payload: SaveRequest, user: dict = Depends(get_current_user)):
    if not _WORK_ID_RE.fullmatch(work_id):
        raise HTTPException(404, "作品不存在。")
    _sweep_gc()
    document = _validate_document(payload.document)
    user_id = user["id"]

    lock = _lock_for(work_id)
    with lock:
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT asset_version, title FROM works WHERE id = ? AND user_id = ?",
                (work_id, user_id),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise HTTPException(404, "作品不存在。")

        old_version = row["asset_version"]
        new_version = secrets.token_hex(16)
        title = (payload.title or "").strip() or (row["title"] or _default_title(document))
        meta = json.dumps(
            {"style": payload.style, "copy": payload.copy_data or {}, "productName": document.get("productName")},
            ensure_ascii=False,
        )

        try:
            staging_parent, version_dir, rewritten = _build_staging(work_id, new_version, old_version, document)
        except StaleResourceError:
            raise HTTPException(409, "作品已被更新，请刷新后重试。")
        except HTTPException:
            raise
        except Exception as error:
            raise HTTPException(400, f"保存失败：{error}")

        try:
            target_dir = _commit_version(staging_parent, version_dir, work_id, new_version)
        except OSError as error:
            _cleanup_staging_parent(staging_parent)
            raise HTTPException(500, f"作品目录落盘失败：{error}")
        _cleanup_staging_parent(staging_parent)

        now = _now_iso()
        preview_url = _works_url(work_id, new_version, "preview.jpg")
        connection = get_connection()
        try:
            rowcount = _update_work_cas(
                connection, work_id, user_id, old_version, title, meta,
                json.dumps(rewritten, ensure_ascii=False), preview_url, new_version, now,
            )
        except Exception as error:
            shutil.rmtree(target_dir, ignore_errors=True)  # 补偿
            raise HTTPException(500, f"写入数据库失败：{error}")
        finally:
            connection.close()

        if rowcount != 1:
            shutil.rmtree(target_dir, ignore_errors=True)  # CAS 失败：回滚新版本
            connection = get_connection()
            try:
                still = connection.execute(
                    "SELECT asset_version FROM works WHERE id = ? AND user_id = ?",
                    (work_id, user_id),
                ).fetchone()
            finally:
                connection.close()
            if still is None:
                raise HTTPException(404, "作品不存在。")
            raise HTTPException(409, "作品已被更新，请刷新后重试。")

        # 成功：标记旧版本废弃（best-effort；失败则保留旧版本，交由人工/后续处理）
        if old_version and old_version != new_version:
            old_dir = WORKS_DIR / work_id / old_version
            if old_dir.is_dir():
                try:
                    _mark_retired(old_dir)
                except OSError:
                    pass  # 安全策略：不删除，仅记录日志外的不处理

        return {"id": work_id, "title": title, "previewUrl": preview_url, "updatedAt": now}


@router.delete("/{work_id}")
def delete_work(work_id: str, user: dict = Depends(get_current_user)):
    if not _WORK_ID_RE.fullmatch(work_id):
        raise HTTPException(404, "作品不存在。")
    lock = _lock_for(work_id)
    with lock:
        connection = get_connection()
        try:
            row = connection.execute(
                "SELECT id FROM works WHERE id = ? AND user_id = ?", (work_id, user["id"])
            ).fetchone()
            if row is None:
                raise HTTPException(404, "作品不存在。")
            connection.execute("DELETE FROM works WHERE id = ? AND user_id = ?", (work_id, user["id"]))
            connection.commit()
        finally:
            connection.close()
    # 删除资源目录（best-effort：即使失败也只留下无 DB 引用的孤儿目录）
    shutil.rmtree(WORKS_DIR / work_id, ignore_errors=True)
    return {"ok": True}
