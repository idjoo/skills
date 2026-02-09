#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///
"""List WhatsApp chats and messages.

Usage:
  uv run --with httpx scripts/list_chats.py chats
  uv run --with httpx scripts/list_chats.py overview --limit 10
  uv run --with httpx scripts/list_chats.py messages <chat_id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from waha_client import check, client, pp


def list_chats(session: str, limit: int, offset: int) -> None:
    with client() as c:
        data = check(
            c.get(
                f"/api/{session}/chats",
                params={
                    "limit": limit,
                    "offset": offset,
                    "sortBy": "conversationTimestamp",
                    "sortOrder": "desc",
                },
            )
        )
        if isinstance(data, list):
            for chat in data:
                print(f"  {chat.get('id', '?')}  {chat.get('name', '')}")
            print(f"\n({len(data)} chats)")
        else:
            pp(data)


def list_overview(session: str, limit: int, offset: int) -> None:
    with client() as c:
        data = check(
            c.get(
                f"/api/{session}/chats/overview",
                params={"limit": limit, "offset": offset},
            )
        )
        if isinstance(data, list):
            for chat in data:
                last = chat.get("lastMessage") or {}
                body = (last.get("body") or "")[:80]
                print(f"  {chat.get('id', '?')}  {chat.get('name', '')}")
                if body:
                    print(f"    -> {body}")
            print(f"\n({len(data)} chats)")
        else:
            pp(data)


def list_messages(
    session: str, chat_id: str, limit: int, offset: int, download_media: bool
) -> None:
    with client() as c:
        data = check(
            c.get(
                f"/api/{session}/chats/{chat_id}/messages",
                params={
                    "limit": limit,
                    "offset": offset,
                    "downloadMedia": str(download_media).lower(),
                    "sortBy": "timestamp",
                    "sortOrder": "desc",
                },
            )
        )
        if isinstance(data, list):
            for msg in reversed(data):
                sender = "me" if msg.get("fromMe") else msg.get("from", "?")
                media = " [media]" if msg.get("hasMedia") else ""
                print(
                    f"  [{msg.get('timestamp', '')}] {sender}: {msg.get('body', '')}{media}"
                )
                print(f"           id: {msg.get('id', '')}")
            print(f"\n({len(data)} messages)")
        else:
            pp(data)


def main() -> None:
    p = argparse.ArgumentParser(description="List WhatsApp chats and messages")
    p.add_argument("-s", "--session", default="default")
    p.add_argument("-l", "--limit", type=int, default=20)
    p.add_argument("--offset", type=int, default=0)
    p.add_argument("--download-media", action="store_true")

    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("chats", help="List chats")
    sub.add_parser("overview", help="Chats with last message preview")
    msg_p = sub.add_parser("messages", help="Get messages from a chat")
    msg_p.add_argument("chat_id", help="Chat ID")

    args = p.parse_args()
    if args.command == "chats":
        list_chats(args.session, args.limit, args.offset)
    elif args.command == "overview":
        list_overview(args.session, args.limit, args.offset)
    elif args.command == "messages":
        list_messages(
            args.session, args.chat_id, args.limit, args.offset, args.download_media
        )


if __name__ == "__main__":
    main()
