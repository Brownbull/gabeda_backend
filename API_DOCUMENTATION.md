# GabeDA API Documentation

## Base URL
```
http://127.0.0.1:8000/api
```

## Authentication

All endpoints except registration and login require JWT authentication.

**Include in headers:**
```
Authorization: Bearer <access_token>
```

---

## Authentication Endpoints

### 1. Register New User

**Endpoint:** `POST /api/accounts/auth/register/`
**Authentication:** Not required

**Request Body:**
```json
{
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "password": "SecurePassword123!",
  "password2": "SecurePassword123!"
}
```

**Response (201 Created):**
```json
{
  "user": {
    "id": "uuid-string",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "is_active": true,
    "created_at": "2025-10-29T12:00:00Z"
  },
  "message": "User registered successfully. Please login to get your access token."
}
```

---

### 2. Login (Get Tokens)

**Endpoint:** `POST /api/accounts/auth/login/`
**Authentication:** Not required

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Token Lifetime:**
- Access Token: 60 minutes
- Refresh Token: 1 day

---

### 3. Refresh Access Token

**Endpoint:** `POST /api/accounts/auth/token/refresh/`
**Authentication:** Not required

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200 OK):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

---

## User Profile Endpoints

### 4. Get Current User Profile

**Endpoint:** `GET /api/accounts/profile/`
**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "is_active": true,
  "created_at": "2025-10-29T12:00:00Z"
}
```

---

### 5. Update User Profile

**Endpoint:** `PUT /api/accounts/profile/` or `PATCH /api/accounts/profile/`
**Authentication:** Required

**Request Body (PATCH for partial update):**
```json
{
  "first_name": "Jane",
  "last_name": "Smith"
}
```

**Response (200 OK):**
```json
{
  "id": "uuid-string",
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Smith",
  "is_active": true,
  "created_at": "2025-10-29T12:00:00Z"
}
```

---

## Company Endpoints

### 6. List User's Companies

**Endpoint:** `GET /api/accounts/companies/`
**Authentication:** Required

**Response (200 OK):**
```json
[
  {
    "id": "company-uuid",
    "name": "Test Company",
    "industry": "retail",
    "location": "Santiago, Chile",
    "column_config": {
      "date_col": "fecha",
      "product_col": "producto",
      "revenue_col": "total"
    },
    "currency": "CLP",
    "top_products_threshold": 0.20,
    "dead_stock_days": 30,
    "created_at": "2025-10-29T12:00:00Z",
    "created_by": "user-uuid",
    "created_by_email": "user@example.com",
    "member_count": 1
  }
]
```

---

### 7. Create New Company

**Endpoint:** `POST /api/accounts/companies/`
**Authentication:** Required

**Request Body:**
```json
{
  "name": "My Company",
  "industry": "retail",
  "location": "Santiago, Chile",
  "currency": "CLP",
  "top_products_threshold": 0.20,
  "dead_stock_days": 30,
  "column_config": {
    "date_col": "fecha",
    "product_col": "producto",
    "description_col": "glosa",
    "revenue_col": "total",
    "quantity_col": "cantidad",
    "transaction_col": "trans_id"
  }
}
```

**Industry Choices:**
- `retail`
- `hospitality`
- `auto_parts`
- `pharma`
- `food_beverage`
- `clothing`
- `books`
- `other`

**Response (201 Created):**
```json
{
  "id": "company-uuid",
  "name": "My Company",
  "industry": "retail",
  "location": "Santiago, Chile",
  "column_config": { ... },
  "currency": "CLP",
  "top_products_threshold": 0.20,
  "dead_stock_days": 30,
  "created_at": "2025-10-29T12:00:00Z",
  "created_by": "user-uuid",
  "created_by_email": "user@example.com",
  "member_count": 1
}
```

**Note:** The user who creates the company is automatically added as an `admin` member.

---

### 8. Get Company Details

**Endpoint:** `GET /api/accounts/companies/{id}/`
**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": "company-uuid",
  "name": "My Company",
  "industry": "retail",
  "location": "Santiago, Chile",
  "column_config": { ... },
  "currency": "CLP",
  "top_products_threshold": 0.20,
  "dead_stock_days": 30,
  "created_at": "2025-10-29T12:00:00Z",
  "created_by": "user-uuid",
  "created_by_email": "user@example.com",
  "member_count": 1
}
```

---

### 9. Update Company

**Endpoint:** `PUT /api/accounts/companies/{id}/` or `PATCH /api/accounts/companies/{id}/`
**Authentication:** Required

**Request Body (PATCH for partial update):**
```json
{
  "name": "Updated Company Name",
  "top_products_threshold": 0.25
}
```

**Response (200 OK):**
```json
{
  "id": "company-uuid",
  "name": "Updated Company Name",
  "industry": "retail",
  "location": "Santiago, Chile",
  "column_config": { ... },
  "currency": "CLP",
  "top_products_threshold": 0.25,
  "dead_stock_days": 30,
  "created_at": "2025-10-29T12:00:00Z",
  "created_by": "user-uuid",
  "created_by_email": "user@example.com",
  "member_count": 1
}
```

---

### 10. Delete Company

**Endpoint:** `DELETE /api/accounts/companies/{id}/`
**Authentication:** Required
**Permission:** Admin only

**Response (204 No Content):**
```
(No response body)
```

---

## Company Member Endpoints

### 11. List Company Members

**Endpoint:** `GET /api/accounts/companies/{id}/members/`
**Authentication:** Required

**Response (200 OK):**
```json
[
  {
    "id": "member-uuid",
    "company": "company-uuid",
    "company_name": "My Company",
    "user": "user-uuid",
    "user_email": "user@example.com",
    "user_name": "John Doe",
    "role": "admin",
    "joined_at": "2025-10-29T12:00:00Z"
  }
]
```

**Role Choices:**
- `admin` - Full access, can manage members
- `business_owner` - Access to all analytics
- `analyst` - Access to detailed analytics
- `operations_manager` - Access to operational metrics

---

### 12. Add Member to Company

**Endpoint:** `POST /api/accounts/companies/{id}/add_member/`
**Authentication:** Required
**Permission:** Admin only

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "role": "analyst"
}
```

**Response (201 Created):**
```json
{
  "id": "member-uuid",
  "company": "company-uuid",
  "company_name": "My Company",
  "user": "user-uuid",
  "user_email": "newuser@example.com",
  "user_name": "New User",
  "role": "analyst",
  "joined_at": "2025-10-29T12:00:00Z"
}
```

**Error Response (403 Forbidden):**
```json
{
  "error": "Only administrators can add members."
}
```

**Error Response (400 Bad Request):**
```json
{
  "email": ["User with this email does not exist."]
}
```

---

### 13. Remove Member from Company

**Endpoint:** `DELETE /api/accounts/companies/{id}/remove_member/`
**Authentication:** Required
**Permission:** Admin only

**Request Body:**
```json
{
  "user_id": "user-uuid"
}
```

**Response (204 No Content):**
```json
{
  "message": "Member removed successfully."
}
```

**Error Response (403 Forbidden):**
```json
{
  "error": "Only administrators can remove members."
}
```

---

### 14. List User's Memberships

**Endpoint:** `GET /api/accounts/memberships/`
**Authentication:** Required

**Response (200 OK):**
```json
[
  {
    "id": "member-uuid",
    "company": "company-uuid",
    "company_name": "My Company",
    "user": "user-uuid",
    "user_email": "user@example.com",
    "user_name": "John Doe",
    "role": "admin",
    "joined_at": "2025-10-29T12:00:00Z"
  }
]
```

---

## Error Responses

### 400 Bad Request
```json
{
  "field_name": ["Error message"]
}
```

### 401 Unauthorized
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### 403 Forbidden
```json
{
  "detail": "You do not have permission to perform this action."
}
```

### 404 Not Found
```json
{
  "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error."
}
```

---

## Testing with cURL

### Register User
```bash
curl -X POST http://127.0.0.1:8000/api/accounts/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "first_name": "Test",
    "last_name": "User",
    "password": "TestPassword123!",
    "password2": "TestPassword123!"
  }'
```

### Login
```bash
curl -X POST http://127.0.0.1:8000/api/accounts/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'
```

### Get Profile (with token)
```bash
curl -X GET http://127.0.0.1:8000/api/accounts/profile/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Create Company
```bash
curl -X POST http://127.0.0.1:8000/api/accounts/companies/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Company",
    "industry": "retail",
    "location": "Santiago, Chile",
    "currency": "CLP"
  }'
```

---

## Testing with Python

See [test_api.py](test_api.py) for a complete Python example using the `requests` library.

**Run the test:**
```bash
# Start Django server
python manage.py runserver

# In separate terminal, run test
python test_api.py
```

---

## Next Steps

Coming soon:
- **CSV Upload API** - Upload transaction data
- **Analytics API** - Retrieve generated insights, KPIs, dashboards
- **Dataset API** - Access generated datasets
- **Export API** - Export data to Excel, PDF
