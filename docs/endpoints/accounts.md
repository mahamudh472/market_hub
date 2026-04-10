# Accounts API Details

Base path: `/api/v1/accounts/`

## Auth and Registration

### POST `/{user_type}/login/`
- Path params:
  - `user_type`: `customer` | `vendor` | `admin`
- Request body:
```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```
- Response 200 (JWT):
```json
{
  "refresh": "...",
  "access": "...",
  "role": "customer",
  "vendor_profile_status": null,
  "vendor_last_submitted_at": null
}
```
- Response 400: invalid role/credentials or role mismatch.

### POST `/logout/`
- Auth: required
- Request body:
```json
{
  "refresh_token": "<refresh_token>"
}
```
- Response 205:
```json
{"message": "Successfully logged out"}
```

### POST `/token/refresh/`
- Request body:
```json
{"refresh": "<refresh_token>"}
```
- Response 200:
```json
{"access": "<new_access_token>"}
```

### POST `/{user_type}/register/`
- Path params:
  - `user_type`: `customer` | `vendor`
- Request body:
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "password": "StrongPass123"
}
```
- Response 200:
```json
{"message": "Otp sent to your email"}
```

### POST `/verify-email/`
- Request body:
```json
{
  "email": "john@example.com",
  "otp": "123456"
}
```
- Response 200:
```json
{"message": "Email john@example.com successfully verified"}
```

## OTP and Password Reset

### POST `/password-reset/` or `/send-otp/`
- Request body:
```json
{"email": "john@example.com"}
```
- Response 200:
```json
{"message": "OTP sent to your email"}
```

### POST `/check-otp/`
- Request body:
```json
{
  "email": "john@example.com",
  "otp": "123456"
}
```
- Response 200:
```json
{"message": "OTP is valid"}
```

### POST `/password-reset-confirm/`
- Request body:
```json
{
  "email": "john@example.com",
  "otp": "123456",
  "new_password": "NewStrongPass123"
}
```
- Response 200:
```json
{"message": "Password for john@example.com successfully reset"}
```

### POST `/change-password/`
- Auth: required
- Request body:
```json
{
  "old_password": "OldPass123",
  "new_password": "NewPass123",
  "confirm_password": "NewPass123"
}
```
- Response 200:
```json
{"message": "Password changed successfully"}
```

## Customer Profile

### GET `/customer/profile/`
- Auth: required
- Query params: none
- Response 200: customer profile with `user`, `recent_orders`, `total_orders`, `total_saved_addresses`.

### PATCH `/customer/profile/update/`
- Auth: required
- Request body (partial, examples):
```json
{
  "full_name": "Updated Name",
  "avatar": "<file>"
}
```
- Response 200: updated user object.

## Customer Address

### GET `/customer/profile/address/`
- Auth: required
- Query params: none
- Response 200: list of addresses.

### POST `/customer/profile/address/`
- Auth: required
- Request body:
```json
{
  "label": "Home",
  "full_name": "John Doe",
  "phone_number": "017xxxxxxxx",
  "address_line1": "House 1, Road 2",
  "address_line2": "Block C",
  "city": 1,
  "zone": 10,
  "postal_code": "1206",
  "country": "Bangladesh",
  "is_default": true
}
```
- Response 201: created address payload.

## Vendor Profile (via accounts routes)

### GET `/vendor/profile/`
- Auth: required (vendor)
- Response 200: vendor detail payload.

### PUT/PATCH `/vendor/profile/update/`
- Auth: required (vendor)
- Request body: partial/full vendor profile fields.
- Response 200: updated vendor detail payload.

### PATCH `/vendor/profile/submit/`
- Auth: required (vendor)
- Request body (all optional, partial update accepted):
```json
{
  "name": "Store Name",
  "description": "Store details",
  "contact_email": "store@example.com",
  "contact_phone": "017xxxxxxxx",
  "address": "Dhaka",
  "city": 1,
  "zone": 10,
  "area": 25,
  "country": "Bangladesh"
}
```
- Response 200:
```json
{
  "message": "Vendor profile submitted successfully. It is now pending admin review.",
  "status": "pending",
  "last_submitted_at": "2026-04-10T10:00:00Z",
  "can_resubmit": true,
  "blocked": false,
  "vendor_profile": {
    "id": 1,
    "name": "Store Name",
    "slug": "store-name"
  }
}
```
