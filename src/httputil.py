from __future__ import annotations

import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

from .config import USER_AGENT

_CTX: Optional[ssl.SSLContext] = None


def _ssl_context() -> ssl.SSLContext:
    global _CTX
    if _CTX is not None:
        return _CTX
    candidates = [
        os.environ.get("SSL_CERT_FILE"),
        os.environ.get("REQUESTS_CA_BUNDLE"),
        "/etc/ssl/certs/ca-certificates.crt",
        "/etc/pki/tls/certs/ca-bundle.crt",
        "/etc/ssl/cert.pem",
    ]
    for ca in candidates:
        if ca and Path(ca).exists():
            _CTX = ssl.create_default_context(cafile=ca)
            return _CTX
    try:
        import certifi  # type: ignore

        _CTX = ssl.create_default_context(cafile=certifi.where())
        return _CTX
    except Exception:
        _CTX = ssl.create_default_context()
        return _CTX


def http_get(url: str, timeout: int = 60, retries: int = 4) -> bytes:
    last: Optional[Exception] = None
    ctx = _ssl_context()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (404, 400):
                raise
            time.sleep(1.5 * (attempt + 1))
    assert last is not None
    raise last


def http_post(url: str, data: bytes, timeout: int = 180, retries: int = 3) -> bytes:
    last: Optional[Exception] = None
    ctx = _ssl_context()
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "User-Agent": USER_AGENT,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return resp.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            time.sleep(2.0 * (attempt + 1))
    assert last is not None
    raise last
