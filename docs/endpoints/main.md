# Main API Details

Base path: `/api/v1/`

## Wishlist

All wishlist endpoints require authentication.

### GET `/wishlist/`
- Query params: none
- Response 200:
```json
[
  {
    "id": 1,
    "product": {
      "id": "<product_uuid>",
      "name": "Product Name",
      "price": "100.00"
    },
    "added_at": "2026-04-10T08:00:00Z"
  }
]
```

### POST `/wishlist/{product_id}/toggle/`
- Path params:
  - `product_id`: product UUID
- Request body: none
- Response 201 (added):
```json
{"added": true, "message": "Added to wishlist."}
```
- Response 200 (removed):
```json
{"added": false, "message": "Removed from wishlist."}
```

### DELETE `/wishlist/{product_id}/`
- Path params:
  - `product_id`: product UUID
- Request body: none
- Response 200:
```json
{"message": "Removed from wishlist."}
```
- Response 404:
```json
{"error": "Product not in your wishlist."}
```
