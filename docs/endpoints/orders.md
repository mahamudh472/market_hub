# Orders API Details

Base path: `/api/v1/orders/`

## Orders

### GET `/`
- Auth: required
- Query params: none
- Response 200: list of current user orders.

### GET `/{order_uuid}/`
- Auth: required
- Query params: none
- Response 200: single order detail with `items` and `payment`.

## Pathao Location APIs

### GET `/pathao/cities/`
- Auth: not required
- Query params: none
- Response 200:
```json
{
  "count": 2,
  "results": [
    {"city_id": 1, "city_name": "Dhaka"}
  ]
}
```

### GET `/pathao/zones/`
- Auth: not required
- Query params:
  - `city_id` (required, integer)
- Response 200:
```json
{
  "city_id": 1,
  "count": 2,
  "results": [
    {"zone_id": 11, "zone_name": "Uttara", "city_id": 1}
  ]
}
```

### GET `/pathao/areas/`
- Auth: not required
- Query params:
  - `zone_id` (required, integer)
- Response 200:
```json
{
  "zone_id": 11,
  "count": 1,
  "results": [
    {
      "area_id": 101,
      "area_name": "Sector 10",
      "zone_id": 11,
      "home_delivery_available": true,
      "pickup_available": true
    }
  ]
}
```

## Pathao Utility/Test Endpoints

### GET `/test-pathao/`
- Purpose: integration debug endpoint.
- Response 200: combined sample cities/zones/areas from Pathao.

### GET `/get-stores/`
- Purpose: integration debug endpoint.
- Response 200:
```json
{"stores": ["..."]}
```

### POST `/create-store/`
- Purpose: integration debug endpoint.
- Request body: none (server uses hardcoded sample store data).
- Response 200:
```json
{"store_creation_response": {"...": "..."}}
```

## Delivery Charge

### POST `/calculate-delivery-charge/`
- Auth: required
- Request body:
```json
{
  "vendor_id": 5,
  "address_id": 9,
  "item_type": 2,
  "delivery_type": 48,
  "item_weight": 0.5
}
```
- Response 200:
```json
{
  "delivery_charge": {
    "...": "Pathao pricing response"
  }
}
```
- Validation:
  - `vendor_id` and `address_id` are required.
  - Address must belong to authenticated user.
  - Vendor must have `pathao_store_id`.
