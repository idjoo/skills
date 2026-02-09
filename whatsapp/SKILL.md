---
name: whatsapp
description: "Send and manage WhatsApp messages via WAHA HTTP API. Use when the user wants to send WhatsApp messages (text, image, video, voice, file), read chats/messages, manage contacts, groups, or sessions. Triggers on: 'send a WhatsApp message', 'check my WhatsApp chats', 'send image on WhatsApp', 'WhatsApp group', 'WhatsApp session', or any WhatsApp-related task."
---

# WhatsApp (WAHA API)

Interact with WhatsApp via [WAHA](https://waha.devlike.pro/) HTTP API. All scripts use `uv run --with httpx` and read config from `~/documents/whatsapp/.env`.

## Configuration

Scripts auto-load `~/documents/whatsapp/.env`. Required variables:

- `WAHA_API_KEY` - API key (sent as `X-Api-Key` header)
- `WAHA_BASE_URL` - Base URL (e.g. `https://whatsapp.wyvern-vector.ts.net`)

## Chat ID Format

- Personal: `<phone>@c.us` (e.g. `6281234567890@c.us`)
- Group: `<id>@g.us` (e.g. `120363012345678901@g.us`)

## Scripts

All scripts are in `scripts/` and share `scripts/waha_client.py` for auth/config.

### Send Text

```bash
uv run --with httpx scripts/send_message.py <chat_id> "message"
uv run --with httpx scripts/send_message.py 6281234567890@c.us "Hello!" --reply-to <msg_id>
```

### Send Media

```bash
uv run --with httpx scripts/send_media.py image <chat_id> <url> --caption "text"
uv run --with httpx scripts/send_media.py file <chat_id> <url>
uv run --with httpx scripts/send_media.py video <chat_id> <url>
uv run --with httpx scripts/send_media.py voice <chat_id> <url>
```

### List Chats & Messages

```bash
uv run --with httpx scripts/list_chats.py chats
uv run --with httpx scripts/list_chats.py overview --limit 5
uv run --with httpx scripts/list_chats.py messages <chat_id> --limit 20
```

### Contacts

```bash
uv run --with httpx scripts/contacts.py list
uv run --with httpx scripts/contacts.py info <contact_id>
uv run --with httpx scripts/contacts.py check <phone_number>
uv run --with httpx scripts/contacts.py block <contact_id>
uv run --with httpx scripts/contacts.py unblock <contact_id>
```

### Groups

```bash
uv run --with httpx scripts/groups.py list
uv run --with httpx scripts/groups.py info <group_id>
uv run --with httpx scripts/groups.py participants <group_id>
uv run --with httpx scripts/groups.py create "Name" user1@c.us user2@c.us
```

### Sessions

```bash
uv run --with httpx scripts/session.py list
uv run --with httpx scripts/session.py info default
uv run --with httpx scripts/session.py start|stop|restart|logout default
```

## Direct API Calls

For operations not covered by scripts, call the API directly. See [references/api_reference.md](references/api_reference.md) for all endpoints and schemas.

Example with httpx:

```python
from waha_client import client, check, pp
with client() as c:
    pp(check(c.put("/api/reaction", json={"messageId": "msg_id", "reaction": "👍", "session": "default"})))
```
