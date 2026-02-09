#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///
"""Manage WhatsApp contacts.

Usage:
  uv run --with httpx scripts/contacts.py list
  uv run --with httpx scripts/contacts.py info <contact_id>
  uv run --with httpx scripts/contacts.py check <phone_number>
  uv run --with httpx scripts/contacts.py block <contact_id>
  uv run --with httpx scripts/contacts.py unblock <contact_id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from waha_client import check, client, pp


def main() -> None:
    p = argparse.ArgumentParser(description="Manage WhatsApp contacts")
    p.add_argument("-s", "--session", default="default")

    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List all contacts")
    sub.add_parser("info").add_argument(
        "contact_id", help="Contact ID (e.g. 6281234567890@c.us)"
    )
    sub.add_parser("check").add_argument(
        "phone", help="Phone number (e.g. 6281234567890)"
    )
    sub.add_parser("block").add_argument("contact_id")
    sub.add_parser("unblock").add_argument("contact_id")

    args = p.parse_args()

    with client() as c:
        if args.command == "list":
            data = check(c.get("/api/contacts/all", params={"session": args.session}))
            if isinstance(data, list):
                for ct in data:
                    print(
                        f"  {ct.get('id', '?')}  {ct.get('name', ct.get('pushname', ''))}"
                    )
                print(f"\n({len(data)} contacts)")
            else:
                pp(data)
        elif args.command == "info":
            pp(
                check(
                    c.get(
                        "/api/contacts",
                        params={"session": args.session, "contactId": args.contact_id},
                    )
                )
            )
        elif args.command == "check":
            data = check(
                c.get(
                    "/api/contacts/check-exists",
                    params={"session": args.session, "phone": args.phone},
                )
            )
            pp(data)
            if isinstance(data, dict):
                exists = data.get("numberExists") or data.get("chatId")
                status = "exists" if exists else "NOT found"
                print(f"\n  Number {args.phone} {status} on WhatsApp")
        elif args.command == "block":
            pp(
                check(
                    c.post(
                        "/api/contacts/block",
                        json={"session": args.session, "contactId": args.contact_id},
                    )
                )
            )
        elif args.command == "unblock":
            pp(
                check(
                    c.post(
                        "/api/contacts/unblock",
                        json={"session": args.session, "contactId": args.contact_id},
                    )
                )
            )


if __name__ == "__main__":
    main()
