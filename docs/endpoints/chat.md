# Chat API Details

Base path: `/api/v1/chat/`

All chat endpoints require authentication.

## Conversations

### GET `/conversations/`
- Query params: none
- Response 200: list of conversations visible to authenticated user.
- Each item includes:
  - `participant`
  - `last_message`, `last_message_at`
  - `last_message_object`
  - `unread_count`

### POST `/conversations/`
- Request body:
```json
{
  "vendor_id": "<vendor_user_uuid>",
  "product_id": "<product_uuid_optional>"
}
```
- Rules:
  - only customers can start conversation
  - if `product_id` is provided, vendor must own that product
- Response 201/200: conversation detail payload.

### GET `/conversations/{conversation_id}/`
- Query params: none
- Response 200: conversation with full `messages` list and `unread_count`.

## Messages

### POST `/conversations/{conversation_id}/messages/`
- Content type: `application/json` (text) or `multipart/form-data` (file)
- Request body examples:
```json
{"text": "Hello, is this available?"}
```
```json
{
  "text": "Please check this",
  "file": "<file>"
}
```
- Validation: either `text` or `file` is required.
- Response 201: created message payload.

### POST `/conversations/{conversation_id}/read/`
- Request body: none
- Response 200:
```json
{"updated": 3}
```
- Meaning: number of unread messages marked as read.
