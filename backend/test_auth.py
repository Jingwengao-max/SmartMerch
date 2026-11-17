"""Authentication origin checks, including HTTPS reverse proxies."""

import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from auth import _verify_origin


def _request(origin: str, *, host: str = "internal:8000",
             forwarded_proto: str = "", forwarded_host: str = "") -> Request:
    headers = [(b"host", host.encode()), (b"origin", origin.encode())]
    if forwarded_proto:
        headers.append((b"x-forwarded-proto", forwarded_proto.encode()))
    if forwarded_host:
        headers.append((b"x-forwarded-host", forwarded_host.encode()))
    return Request({
        "type": "http",
        "method": "POST",
        "scheme": "http",
        "server": ("internal", 8000),
        "path": "/api/auth/login",
        "query_string": b"",
        "headers": headers,
    })


class OriginVerificationTests(unittest.TestCase):
    def test_accepts_https_origin_reported_by_reverse_proxy(self):
        request = _request(
            "https://smartmerch.example.com",
            forwarded_proto="https",
            forwarded_host="smartmerch.example.com",
        )
        _verify_origin(request)

    def test_accepts_configured_production_origin(self):
        with patch.dict(os.environ, {
            "SMARTMERCH_ALLOWED_ORIGINS": "https://smartmerch.example.com"
        }):
            _verify_origin(_request("https://smartmerch.example.com"))

    def test_rejects_unrelated_origin(self):
        request = _request(
            "https://attacker.example",
            forwarded_proto="https",
            forwarded_host="smartmerch.example.com",
        )
        with self.assertRaises(HTTPException) as raised:
            _verify_origin(request)
        self.assertEqual(raised.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
