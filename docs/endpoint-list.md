# API Endpoint List

Base URL: `/api/v1`

## Accounts (`/api/v1/accounts`)

| Method | Endpoint | Description | Docs |
|---|---|---|---|
| POST | `/api/v1/accounts/{user_type}/login/` | Login with JWT (`user_type`: `customer`, `vendor`, `admin`). | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/logout/` | Logout and blacklist refresh token. | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/token/refresh/` | Refresh access token using refresh token. | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/{user_type}/register/` | Register customer/vendor and send OTP. | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/verify-email/` | Verify account email with OTP. | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/password-reset/` | Send OTP for password reset. | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/send-otp/` | Send OTP to existing user. | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/check-otp/` | Validate OTP without consuming it. | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/password-reset-confirm/` | Reset password with OTP. | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/change-password/` | Change password for logged in user. | [Details](endpoints/accounts.md) |
| GET | `/api/v1/accounts/customer/profile/` | Get customer profile. | [Details](endpoints/accounts.md) |
| PATCH | `/api/v1/accounts/customer/profile/update/` | Update authenticated user profile fields. | [Details](endpoints/accounts.md) |
| GET | `/api/v1/accounts/customer/profile/address/` | List customer saved addresses. | [Details](endpoints/accounts.md) |
| POST | `/api/v1/accounts/customer/profile/address/` | Add a new customer address. | [Details](endpoints/accounts.md) |
| GET | `/api/v1/accounts/vendor/profile/` | Get authenticated vendor profile. | [Details](endpoints/accounts.md) |
| PUT/PATCH | `/api/v1/accounts/vendor/profile/update/` | Update authenticated vendor profile. | [Details](endpoints/accounts.md) |
| PATCH | `/api/v1/accounts/vendor/profile/submit/` | Submit/re-submit vendor profile for review. | [Details](endpoints/accounts.md) |

## Main (`/api/v1`)

| Method | Endpoint | Description | Docs |
|---|---|---|---|
| GET | `/api/v1/wishlist/` | List logged-in user wishlist items. | [Details](endpoints/main.md) |
| POST | `/api/v1/wishlist/{product_id}/toggle/` | Toggle add/remove item from wishlist. | [Details](endpoints/main.md) |
| DELETE | `/api/v1/wishlist/{product_id}/` | Remove item from wishlist. | [Details](endpoints/main.md) |

## Products (`/api/v1/products`)

| Method | Endpoint | Description | Docs |
|---|---|---|---|
| GET | `/api/v1/products/categories/` | List top-level categories with product count. | [Details](endpoints/products.md) |
| GET | `/api/v1/products/categories/{slug}/` | List products by category slug (supports filters/sort). | [Details](endpoints/products.md) |
| GET | `/api/v1/products/search/` | Search products by query string `q`. | [Details](endpoints/products.md) |
| GET | `/api/v1/products/{product_uuid}/` | Product detail with related products and delivery info. | [Details](endpoints/products.md) |
| GET | `/api/v1/products/{product_uuid}/reviews/` | List product reviews (paginated). | [Details](endpoints/products.md) |
| POST | `/api/v1/products/{product_uuid}/reviews/add/` | Add review for product (auth required). | [Details](endpoints/products.md) |

## Cart (`/api/v1/cart`)

| Method | Endpoint | Description | Docs |
|---|---|---|---|
| GET | `/api/v1/cart/` | Get current user cart details and totals. | [Details](endpoints/cart.md) |
| POST | `/api/v1/cart/items/` | Add item to cart. | [Details](endpoints/cart.md) |
| PATCH | `/api/v1/cart/items/{item_id}/` | Update item quantity. | [Details](endpoints/cart.md) |
| DELETE | `/api/v1/cart/items/{item_id}/delete/` | Delete item from cart. | [Details](endpoints/cart.md) |
| DELETE | `/api/v1/cart/clear/` | Remove all items from cart. | [Details](endpoints/cart.md) |
| POST | `/api/v1/cart/voucher/apply/` | Apply voucher code to cart. | [Details](endpoints/cart.md) |
| DELETE | `/api/v1/cart/voucher/remove/` | Remove applied voucher. | [Details](endpoints/cart.md) |

## Orders (`/api/v1/orders`)

| Method | Endpoint | Description | Docs |
|---|---|---|---|
| GET | `/api/v1/orders/` | List authenticated user orders. | [Details](endpoints/orders.md) |
| GET | `/api/v1/orders/{order_uuid}/` | Get order detail. | [Details](endpoints/orders.md) |
| GET | `/api/v1/orders/pathao/cities/` | List Pathao cities. | [Details](endpoints/orders.md) |
| GET | `/api/v1/orders/pathao/zones/?city_id={id}` | List Pathao zones by city. | [Details](endpoints/orders.md) |
| GET | `/api/v1/orders/pathao/areas/?zone_id={id}` | List Pathao areas by zone. | [Details](endpoints/orders.md) |
| GET | `/api/v1/orders/test-pathao/` | Debug/test Pathao integration. | [Details](endpoints/orders.md) |
| GET | `/api/v1/orders/get-stores/` | Debug/test list Pathao stores. | [Details](endpoints/orders.md) |
| POST | `/api/v1/orders/create-store/` | Debug/test create Pathao store. | [Details](endpoints/orders.md) |
| POST | `/api/v1/orders/calculate-delivery-charge/` | Calculate Pathao delivery charge. | [Details](endpoints/orders.md) |

## Vendor (`/api/v1/vendor`)

| Method | Endpoint | Description | Docs |
|---|---|---|---|
| GET | `/api/v1/vendor/stores/` | List approved active stores. | [Details](endpoints/vendor.md) |
| GET | `/api/v1/vendor/store/` | Get authenticated vendor own store page. | [Details](endpoints/vendor.md) |
| GET | `/api/v1/vendor/store/{slug}/` | Get public store details by slug. | [Details](endpoints/vendor.md) |

## Chat (`/api/v1/chat`)

| Method | Endpoint | Description | Docs |
|---|---|---|---|
| GET | `/api/v1/chat/conversations/` | List user conversations. | [Details](endpoints/chat.md) |
| POST | `/api/v1/chat/conversations/` | Create (or reuse) conversation. | [Details](endpoints/chat.md) |
| GET | `/api/v1/chat/conversations/{conversation_id}/` | Conversation details with messages. | [Details](endpoints/chat.md) |
| POST | `/api/v1/chat/conversations/{conversation_id}/messages/` | Send text/file message. | [Details](endpoints/chat.md) |
| POST | `/api/v1/chat/conversations/{conversation_id}/read/` | Mark unread messages as read. | [Details](endpoints/chat.md) |

## Notes

- UUID path variables are shown as `{..._uuid}` for readability.
- Auth-required endpoints expect `Authorization: Bearer <access_token>`.
- Detailed payload docs are under `docs/endpoints/`.
