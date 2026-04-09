# Chat API and WebSocket Guide

## REST Endpoints

Base: `/api/v1/chat/`

- `GET /conversations/`
  - List conversations for authenticated user (customer or vendor)
- `POST /conversations/`
  - Customer starts or retrieves a conversation
  - Body:
    ```json
    {
      "vendor_id": "<vendor-user-uuid>",
      "product_id": "<optional-product-uuid>"
    }
    ```
- `GET /conversations/<conversation_id>/`
  - Conversation details with message list
- `POST /conversations/<conversation_id>/messages/`
  - Send message and file via HTTP (recommended for all file uploads)
  - Supports multipart/form-data for file upload
  - Fields:
    - `text` (optional)
    - `file` (optional)
  - At least one of `text` or `file` is required
- `POST /conversations/<conversation_id>/read/`
  - Mark unread messages as read for current user

## WebSocket

URL:
`ws://<host>/ws/chat/<conversation_id>/?token=<access_token>`

Auth is done via JWT access token in query param `token`.
Connection is accepted only if user is part of the conversation.

### Client -> Server payloads

WebSocket text message:
```json
{
  "type": "message",
  "text": "Hello seller"
}
```

File upload flow (HTTP + WebSocket sync):
- 1) Upload file using `POST /api/v1/chat/conversations/<conversation_id>/messages/` with multipart/form-data.
- 2) Backend stores file and creates message.
- 3) Backend emits `chat_message` event to the same conversation room.
- 4) All connected clients instantly receive the new message (with `file_url`) over WebSocket.

Note:
- Sending `file_data` over WebSocket is intentionally rejected.

Mark read:
```json
{
  "type": "mark_read"
}
```

### Server -> Client events

New message:
```json
{
  "type": "message",
  "data": {
    "id": "...",
    "conversation": "...",
    "sender": "...",
    "sender_name": "...",
    "sender_role": "customer|vendor",
    "text": "...",
    "file_url": "/media/chat_files/...",
    "file_name": "...",
    "file_content_type": "...",
    "file_size": 123,
    "is_read": false,
    "read_at": null,
    "created_at": "..."
  }
}
```

Read receipt:
```json
{
  "type": "read_receipt",
  "data": {
    "type": "chat_read_receipt",
    "conversation_id": "...",
    "updated": 2,
    "reader_id": "..."
  }
}
```
