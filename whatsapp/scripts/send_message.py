#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///
"""Send a WhatsApp text message.

Usage: uv run --with httpx scripts/send_message.py <chat_id> "message"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from waha_client import check, client, pp


def main() -> None:
    p = argparse.ArgumentParser(description="Send a WhatsApp text message")
    p.add_argument("chat_id", help="Chat ID (e.g. 6281234567890@c.us)")
    p.add_argument("text", help="Message text")
    p.add_argument("-s", "--session", default="default")
    p.add_argument("-r", "--reply-to", default=None, help="Message ID to reply to")
    args = p.parse_args()

    payload: dict = {"chatId": args.chat_id, "text": args.text, "session": args.session}
    if args.reply_to:
        payload["reply_to"] = args.reply_to

    with client() as c:
        pp(check(c.post("/api/sendText", json=payload)))


if __name__ == "__main__":
    main()
