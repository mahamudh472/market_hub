# Cart API Details

Base path: `/api/v1/cart/`

Auth is required for all cart endpoints.

## Cart

### GET `/`
- Query params: none
- Response 200:
```json
{
  "id": 12,
  "items": [
    {
      "id": 1,
      "quantity": 2,
      "unit_price": "100.00",
      "total_price": "200.00",
      "product_detail": {"id": "...", "name": "Product A"},
      "variant_detail": null
    }
  ],
  "items_count": 1,
  "voucher_detail": null,
  "subtotal": "200.00",
  "discount": "0.00",
  "tax": "0.00",
  "delivery_charge": 60,
  "total": "260.00"
}
```

## Items

### POST `/items/`
- Request body:
```json
{
  "product": "<product_uuid>",
  "variant": "<variant_uuid_optional>",
  "quantity": 1
}
```
- Response 200: full updated cart payload.

### PATCH `/items/{item_id}/`
- Request body:
```json
{"quantity": 3}
```
- Response 200: full updated cart payload.

### DELETE `/items/{item_id}/delete/`
- Request body: none
- Response 200: full updated cart payload.

### DELETE `/clear/`
- Request body: none
- Response 200: full updated (empty) cart payload.

## Voucher

### POST `/voucher/apply/`
- Request body:
```json
{"code": "EID50"}
```
- Response 200:
```json
{
  "message": "Voucher applied successfully.",
  "cart": {"id": 12, "total": "210.00"}
}
```

### DELETE `/voucher/remove/`
- Request body: none
- Response 200: full updated cart payload.
