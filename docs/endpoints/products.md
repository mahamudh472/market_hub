# Products API Details

Base path: `/api/v1/products/`

## Categories

### GET `/categories/`
- Query params: none
- Response 200:
```json
[
  {
    "id": 1,
    "name": "Electronics",
    "slug": "electronics",
    "image": "/media/category_images/...",
    "product_count": 23
  }
]
```

### GET `/categories/{slug}/`
- Query params:
  - `vendor` (optional): vendor id
  - `min_price` (optional)
  - `max_price` (optional)
  - `sort` (optional): `price`, `-price`, `created_at`, `-created_at`, `-product_count`
- Response 200: paginated product list (`count`, `next`, `previous`, `results`).

## Search

### GET `/search/`
- Query params:
  - `q` (required for results)
- Response 200: list of matching products.

## Product Detail

### GET `/{product_uuid}/`
- Query params: none
- Response 200 includes:
  - product core fields (`id`, `name`, `description`, `price`, `stock`, ...)
  - `images`, `variant_types`, `variants`
  - `related_products`
  - `you_may_also_like`
  - `delivery_info`

## Reviews

### GET `/{product_uuid}/reviews/`
- Query params:
  - pagination params (for default DRF paginator, usually `page`)
- Response 200: paginated reviews.

### POST `/{product_uuid}/reviews/add/`
- Auth: required
- Content type: `multipart/form-data` (if uploading images)
- Request body:
```json
{
  "rating": 5,
  "comment": "Excellent product",
  "uploaded_images": ["<file1>", "<file2>"]
}
```
- Response 201:
```json
{"message": "Review submitted successfully."}
```
- Validation notes:
  - rating must be 1..5
  - one review per user per product
