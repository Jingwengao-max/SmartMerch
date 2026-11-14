"""邮箱 + 密码认证：scrypt 密码哈希、服务端 Session + HttpOnly Cookie。

不引入第三方依赖：密码哈希用标准库 hashlib.scrypt，会话 ID 用 secrets，
存储用标准库 sqlite3。Session 只把 SHA-256 哈希写入数据库，明文 token 仅存于
浏览器 HttpOnly Cookie。
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from db import get_connection

COOKIE_NAME = "smartmerch_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DK_LEN = 32
SCRYPT_MAXMEM = 64 * 1024 * 1024

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PASSWORD_MIN = 8

# 合法前端来源（本地开发）。生产单端口同源请求走「同源放行」分支。
ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ── 密码哈希 ──────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DK_LEN,
        maxmem=SCRYPT_MAXMEM,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
            maxmem=SCRYPT_MAXMEM,
        )
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


# ── Session ──────────────────────────────────────────────
def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _expires_at() -> int:
    return int(time.time()) + SESSION_TTL_SECONDS


def _create_session(connection, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    # 顺手清理已过期会话，避免僵尸记录累积。
    connection.execute(
        "DELETE FROM sessions WHERE CAST(expires_at AS INTEGER) <= ?",
        (int(time.time()),),
    )
    connection.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (_hash_token(token), user_id, _now_iso(), str(_expires_at())),
    )
    connection.commit()
    return token


def _get_user_by_session(request: Request) -> dict | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    token_hash = _hash_token(token)
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT u.id, u.email, u.name, s.expires_at "
            "FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash = ?",
            (token_hash,),
        ).fetchone()
        if row is None:
            return None
        if int(row["expires_at"]) <= time.time():
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
            connection.commit()
            return None
        return {"id": row["id"], "email": row["email"], "name": row["name"]}
    finally:
        connection.close()


def _destroy_session(request: Request) -> None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return
    token_hash = _hash_token(token)
    connection = get_connection()
    try:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))
        connection.commit()
    finally:
        connection.close()


# ── Cookie / CSRF ────────────────────────────────────────
def _cookie_secure() -> bool:
    return os.getenv("SMARTMERCH_COOKIE_SECURE", "0") == "1"


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(),
        path="/",
    )


def _verify_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if not origin:
        # 非浏览器客户端（curl 等）不带 Origin；浏览器跨站请求已被 SameSite=Lax 拦截。
        return
    if origin in ALLOWED_ORIGINS:
        return
    scheme = request.url.scheme
    host = request.headers.get("host") or request.url.netloc
    if origin == f"{scheme}://{host}":
        return
    raise HTTPException(403, "非法请求来源。")


# ── 依赖：当前登录用户 ────────────────────────────────────
def get_current_user(request: Request) -> dict:
    user = _get_user_by_session(request)
    if user is None:
        raise HTTPException(401, "未登录。")
    return user


# ── 请求模型 ─────────────────────────────────────────────
class Credentials(BaseModel):
    email: str
    password: str


# ── 接口 ─────────────────────────────────────────────────
def _normalize_credentials(email: str, password: str) -> tuple[str, str]:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(400, "邮箱格式不正确。")
    if len(password) < PASSWORD_MIN:
        raise HTTPException(400, f"密码至少 {PASSWORD_MIN} 位。")
    return email, password


@router.post("/register", status_code=201)
def register(credentials: Credentials, request: Request, response: Response):
    _verify_origin(request)
    email, password = _normalize_credentials(credentials.email, credentials.password)
    connection = get_connection()
    try:
        exists = connection.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone()
        if exists:
            raise HTTPException(409, "该邮箱已注册。")
        user_id = uuid.uuid4().hex
        name = email.split("@")[0]
        connection.execute(
            "INSERT INTO users (id, email, name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, name, hash_password(password), _now_iso()),
        )
        token = _create_session(connection, user_id)
    finally:
        connection.close()
    _set_session_cookie(response, token)
    return {"id": user_id, "email": email, "name": name}


@router.post("/login")
def login(credentials: Credentials, request: Request, response: Response):
    _verify_origin(request)
    email, password = _normalize_credentials(credentials.email, credentials.password)
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT id, email, name, password_hash FROM users WHERE email = ?", (email,)
        ).fetchone()
        if row is None or not verify_password(password, row["password_hash"]):
            raise HTTPException(401, "邮箱或密码错误。")
        user_id = row["id"]
        email_out = row["email"]
        name = row["name"]
        token = _create_session(connection, user_id)
    finally:
        connection.close()
    _set_session_cookie(response, token)
    return {"id": user_id, "email": email_out, "name": name}


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/logout")
def logout(request: Request, response: Response):
    _verify_origin(request)
    _destroy_session(request)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}
