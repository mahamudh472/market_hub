# Vendor API Details

Base path: `/api/v1/vendor/`

## Public Store APIs

### GET `/stores/`
- Query params (pagination): depends on `StandardResultsSetPagination` (commonly `page`, `page_size`).
- Response 200: paginated approved/active stores.

### GET `/store/{slug}/`
- Query params:
  - `category` (optional): category slug filter for products
  - `sort` (optional): `price`, `-price`, `created_at`, `-created_at`
- Response 200:
```json
{
  "vendor": {
    "id": 1,
    "name": "Store Name",
    "slug": "store-name",
    "verification_status": "approved"
  },
  "categories": [
    {"id": 1, "name": "Electronics", "slug": "electronics", "product_count": 4}
  ],
  "products": [
    {"id": "<product_uuid>", "name": "Item A", "price": "100.00"}
  ]
}
```

## Authenticated Vendor Store API

### GET `/store/`
- Auth: required (vendor)
- Behavior:
  - Returns authenticated vendor store data.
  - If vendor is not approved, returns 403 pending/blocked status payload.
- Query params:
  - `category` (optional)
  - `sort` (optional)
- Response 200: same shape as `/store/{slug}/`.
- Response 403 example:
```json
{
  "message": "Your vendor profile is not verified yet.",
  "status": "pending",
  "last_submitted_at": "2026-04-10T10:00:00Z",
  "can_resubmit": true,
  "blocked": false
}
```
