#!/usr/bin/env python3
# /// script
# dependencies = ["httpx"]
# ///
"""Send media (image/file/video/voice) via WhatsApp.

Usage: uv run --with httpx scripts/send_media.py image <chat_id> <url> --caption "text"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from waha_client import check, client, pp

ENDPOINTS = {
    "image": "/api/sendImage",
    "file": "/api/sendFile",
    "video": "/api/sendVideo",
    "voice": "/api/sendVoice",
}


def main() -> None:
    p = argparse.ArgumentParser(description="Send media via WhatsApp")
    p.add_argument("media_type", choices=ENDPOINTS.keys(), help="Type of media")
    p.add_argument("chat_id", help="Chat ID")
    p.add_argument("url", help="URL of the media file")
    p.add_argument("-s", "--session", default="default")
    p.add_argument("-c", "--caption", default=None)
    p.add_argument("-r", "--reply-to", default=None, help="Message ID to reply to")
    p.add_argument("-f", "--filename", default=None)
    p.add_argument("-m", "--mimetype", default=None)
    args = p.parse_args()

    file_obj: dict = {"url": args.url}
    if args.mimetype:
        file_obj["mimetype"] = args.mimetype
    if args.filename:
        file_obj["filename"] = args.filename

    payload: dict = {"chatId": args.chat_id, "file": file_obj, "session": args.session}
    if args.caption:
        payload["caption"] = args.caption
    if args.reply_to:
        payload["reply_to"] = args.reply_to
    if args.media_type in ("video", "voice"):
        payload["convert"] = True

    with client() as c:
        pp(check(c.post(ENDPOINTS[args.media_type], json=payload)))


if __name__ == "__main__":
    main()
