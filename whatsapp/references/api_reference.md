# WAHA API Reference

API: WAHA - WhatsApp HTTP API v2026.2.1 ([docs](https://waha.devlike.pro/))

## Authentication

All requests require header `X-Api-Key: <key>`. Config is in `~/documents/whatsapp/.env`.

## Chat ID Formats

- Personal: `<phone>@c.us` (e.g. `6281234567890@c.us`)
- Group: `<id>@g.us` (e.g. `120363012345678901@g.us`)
- Channel: `<id>@newsletter`

## Endpoints

### Sessions

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/sessions` | List all sessions |
| POST | `/api/sessions` | Create session |
| GET | `/api/sessions/{session}` | Get session info |
| PUT | `/api/sessions/{session}` | Update session |
| DELETE | `/api/sessions/{session}` | Delete session |
| POST | `/api/sessions/{session}/start` | Start session |
| POST | `/api/sessions/{session}/stop` | Stop session |
| POST | `/api/sessions/{session}/restart` | Restart session |
| POST | `/api/sessions/{session}/logout` | Logout session |
| GET | `/api/sessions/{session}/me` | Get authenticated account info |

### Sending Messages

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/sendText` | Send text message |
| POST | `/api/sendImage` | Send image |
| POST | `/api/sendFile` | Send file |
| POST | `/api/sendVideo` | Send video |
| POST | `/api/sendVoice` | Send voice message |
| POST | `/api/sendLocation` | Send location |
| POST | `/api/sendContactVcard` | Send contact vCard |
| POST | `/api/sendPoll` | Send poll |
| POST | `/api/forwardMessage` | Forward message |
| PUT | `/api/reaction` | React to message |
| PUT | `/api/star` | Star/unstar message |
| POST | `/api/sendSeen` | Mark as seen |
| POST | `/api/startTyping` | Start typing indicator |
| POST | `/api/stopTyping` | Stop typing indicator |

### Chats

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/{session}/chats` | List chats (sortable, paginated) |
| GET | `/api/{session}/chats/overview` | Chats with last message preview |
| DELETE | `/api/{session}/chats/{chatId}` | Delete chat |
| GET | `/api/{session}/chats/{chatId}/messages` | Get messages (filterable, paginated) |
| DELETE | `/api/{session}/chats/{chatId}/messages/{messageId}` | Delete message |
| PUT | `/api/{session}/chats/{chatId}/messages/{messageId}` | Edit message |

### Contacts

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/contacts` | Get contact info |
| GET | `/api/contacts/all` | Get all contacts |
| GET | `/api/contacts/check-exists` | Check if phone exists on WhatsApp |
| GET | `/api/contacts/profile-picture` | Get profile picture URL |
| POST | `/api/contacts/block` | Block contact |
| POST | `/api/contacts/unblock` | Unblock contact |

### Groups

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/{session}/groups` | Create group |
| GET | `/api/{session}/groups` | List groups |
| GET | `/api/{session}/groups/{id}` | Get group info |
| DELETE | `/api/{session}/groups/{id}` | Delete group |
| GET | `/api/{session}/groups/{id}/participants` | Get participants |
| POST | `/api/{session}/groups/{id}/participants/add` | Add participants |
| POST | `/api/{session}/groups/{id}/participants/remove` | Remove participants |
| POST | `/api/{session}/groups/{id}/admin/promote` | Promote to admin |
| POST | `/api/{session}/groups/{id}/admin/demote` | Demote from admin |
| POST | `/api/{session}/groups/{id}/leave` | Leave group |
| GET | `/api/{session}/groups/{id}/invite-code` | Get invite code |

### Channels

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/{session}/channels` | List channels |
| POST | `/api/{session}/channels` | Create channel |
| GET | `/api/{session}/channels/{id}` | Get channel info |
| POST | `/api/{session}/channels/{id}/follow` | Follow channel |
| POST | `/api/{session}/channels/{id}/unfollow` | Unfollow channel |

### Status (Stories)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/{session}/status/text` | Post text status |
| POST | `/api/{session}/status/image` | Post image status |
| POST | `/api/{session}/status/video` | Post video status |

### Observability

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/ping` | Ping |
| GET | `/api/version` | Server version |

## Key Request Schemas

### SendText
```json
{"chatId": "6281234567890@c.us", "text": "Hello!", "session": "default", "reply_to": "msg_id"}
```

### SendImage / SendFile
```json
{"chatId": "...", "file": {"url": "https://..."}, "session": "default", "caption": "..."}
```

File can be remote URL (`{"url": "..."}`) or base64 (`{"data": "<b64>", "mimetype": "image/jpeg", "filename": "pic.jpg"}`).

### SendVideo / SendVoice
Same as above, plus `"convert": true` for ffmpeg processing.

### SendLocation
```json
{"chatId": "...", "latitude": -6.2, "longitude": 106.8, "title": "Jakarta", "session": "default"}
```

### SendPoll
```json
{"chatId": "...", "poll": {"name": "Question?", "options": ["A", "B", "C"], "multipleAnswers": false}, "session": "default"}
```

### Reaction
```json
{"messageId": "false_123@c.us_AAA", "reaction": "👍", "session": "default"}
```

## Message Response (WAMessage)
```json
{
  "id": "false_123@c.us_AAA",
  "timestamp": 1666943582,
  "from": "123@c.us",
  "fromMe": false,
  "to": "456@c.us",
  "body": "message text",
  "hasMedia": false,
  "ack": 3,
  "ackName": "READ"
}
```

ACK values: -1=ERROR, 0=PENDING, 1=SERVER, 2=DEVICE, 3=READ, 4=PLAYED.
