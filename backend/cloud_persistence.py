"""Optional Supabase persistence for cloud deployments.

The application keeps working locally when Supabase is not configured. In a
deployment, the secret key stays on the server and is never sent to the
browser.
"""

from __future__ import annotations

import os
from typing import Any

import requests


def cloud_persistence_configured() -> bool:
    return bool(
        os.getenv("SUPABASE_URL", "").strip()
        and _secret_key()
    )


def _secret_key() -> str:
    """Prefer Supabase's current secret key, with legacy upgrade support."""
    return (
        os.getenv("SUPABASE_SECRET_KEY", "").strip()
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
    )


def _write(table: str, payload: dict[str, Any], *, upsert: bool = False) -> bool:
    if not cloud_persistence_configured():
        return False
    base = os.environ["SUPABASE_URL"].strip().rstrip("/")
    key = _secret_key()
    headers = {
        "apikey": key,
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal" if upsert else "return=minimal",
    }
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = f"Bearer {key}"
    try:
        response = requests.post(
            f"{base}/rest/v1/{table}", headers=headers, json=payload, timeout=10,
        )
        response.raise_for_status()
        return True
    except requests.RequestException as error:
        # Database logging must never make poster generation fail.
        print(f"Supabase write skipped ({table}): {error}", flush=True)
        return False


def save_job(payload: dict[str, Any]) -> bool:
    return _write("generation_jobs", payload, upsert=True)


def save_feedback(payload: dict[str, Any]) -> bool:
    return _write("feedback", payload)
