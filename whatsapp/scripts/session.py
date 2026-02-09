#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///
"""Manage WhatsApp sessions.

Usage:
  uv run --with httpx scripts/session.py list
  uv run --with httpx scripts/session.py info default
  uv run --with httpx scripts/session.py start|stop|restart|logout default
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from waha_client import check, client, pp


def main() -> None:
    p = argparse.ArgumentParser(description="Manage WhatsApp sessions")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all sessions")
    sub.add_parser("info").add_argument("name", help="Session name")
    sub.add_parser("start").add_argument("name")
    sub.add_parser("stop").add_argument("name")
    sub.add_parser("restart").add_argument("name")
    sub.add_parser("logout").add_argument("name")

    args = p.parse_args()

    with client() as c:
        if args.command == "list":
            data = check(c.get("/api/sessions"))
            if isinstance(data, list):
                for s in data:
                    print(f"  {s.get('name', '?')}  [{s.get('status', '?')}]")
                print(f"\n({len(data)} sessions)")
            else:
                pp(data)
        elif args.command == "info":
            pp(check(c.get(f"/api/sessions/{args.name}")))
        elif args.command in ("start", "stop", "restart", "logout"):
            pp(check(c.post(f"/api/sessions/{args.name}/{args.command}")))
            print(f"  Session '{args.name}' -> {args.command}")


if __name__ == "__main__":
    main()
