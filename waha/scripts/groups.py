#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///
"""Manage WhatsApp groups.

Usage:
  uv run --with httpx scripts/groups.py list
  uv run --with httpx scripts/groups.py info <group_id>
  uv run --with httpx scripts/groups.py participants <group_id>
  uv run --with httpx scripts/groups.py create "Name" participant1@c.us participant2@c.us
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from waha_client import check, client, pp


def main() -> None:
    p = argparse.ArgumentParser(description="Manage WhatsApp groups")
    p.add_argument("-s", "--session", default="default")

    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List all groups")
    sub.add_parser("info").add_argument(
        "group_id", help="Group ID (e.g. 120363012345678901@g.us)"
    )
    sub.add_parser("participants").add_argument("group_id")
    create_p = sub.add_parser("create")
    create_p.add_argument("name", help="Group name")
    create_p.add_argument("participants", nargs="+", help="Participant chat IDs")

    args = p.parse_args()

    with client() as c:
        if args.command == "list":
            data = check(c.get(f"/api/{args.session}/groups"))
            if isinstance(data, list):
                for g in data:
                    print(
                        f"  {g.get('id', '?')}  {g.get('subject', g.get('name', ''))} ({g.get('size', '?')} members)"
                    )
                print(f"\n({len(data)} groups)")
            else:
                pp(data)
        elif args.command == "info":
            pp(check(c.get(f"/api/{args.session}/groups/{args.group_id}")))
        elif args.command == "participants":
            data = check(
                c.get(f"/api/{args.session}/groups/{args.group_id}/participants")
            )
            if isinstance(data, list):
                for pt in data:
                    print(
                        f"  {pt.get('id', '?')}  {pt.get('role', pt.get('isAdmin', ''))}"
                    )
                print(f"\n({len(data)} participants)")
            else:
                pp(data)
        elif args.command == "create":
            payload = {
                "name": args.name,
                "participants": [{"id": pid} for pid in args.participants],
            }
            pp(check(c.post(f"/api/{args.session}/groups", json=payload)))


if __name__ == "__main__":
    main()
