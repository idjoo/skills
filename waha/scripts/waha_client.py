"""Shared WAHA API client. Loads config from ~/documents/waha/.env."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

_ENV_PATH = Path.home() / "documents" / "waha" / ".env"


def _load_env() -> None:
    if not _ENV_PATH.exists():
        return
    for line in _ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


_load_env()

BASE_URL = os.environ.get("WAHA_BASE_URL", "https://whatsapp.wyvern-vector.ts.net")
API_KEY = os.environ.get("WAHA_API_KEY", "")

if not API_KEY:
    print(
        "Error: WAHA_API_KEY not set. Check ~/documents/waha/.env", file=sys.stderr
    )
    sys.exit(1)


def client() -> httpx.Client:
    return httpx.Client(
        base_url=BASE_URL, headers={"X-Api-Key": API_KEY}, timeout=30.0, verify=False
    )


def pp(data: object) -> None:
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def check(resp: httpx.Response) -> object:
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        die(f"HTTP {resp.status_code}: {detail}")
    return resp.json()
