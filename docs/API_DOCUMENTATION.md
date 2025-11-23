# API Documentation

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://api.bharatbuild.ai/api/v1
```

## Authentication

All authenticated endpoints require a Bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Endpoints

## Authentication

### Register User

```http
POST /auth/register
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123",
  "full_name": "John Doe",
  "role": "student"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "student",
  "is_active": true,
  "is_verified": false,
  "created_at": "2025-01-20T10:00:00Z"
}
```

### Login

```http
POST /auth/login
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Get Current User

```http
GET /auth/me
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "student",
  "is_active": true,
  "is_verified": true,
  "created_at": "2025-01-20T10:00:00Z"
}
```

## Projects

### Create Project

```http
POST /projects
```

**Request Body (Student Mode):**
```json
{
  "title": "E-Commerce Platform",
  "description": "A full-featured e-commerce platform with payment integration",
  "mode": "student",
  "domain": "Web Development",
  "tech_stack": {
    "frontend": "React",
    "backend": "FastAPI",
    "database": "PostgreSQL"
  },
  "features": [
    "User authentication",
    "Product catalog",
    "Shopping cart",
    "Payment integration"
  ]
}
```

**Request Body (Developer Mode):**
```json
{
  "title": "Blog Platform",
  "description": "A modern blog platform with CMS",
  "mode": "developer",
  "framework": "Next.js",
  "deployment_target": "Vercel",
  "features": [
    "Markdown editor",
    "SEO optimization",
    "Analytics dashboard"
  ]
}
```

**Request Body (Founder Mode):**
```json
{
  "title": "AI-Powered Analytics Tool",
  "description": "Analytics platform for small businesses",
  "mode": "founder",
  "industry": "SaaS",
  "target_market": "Small businesses",
  "features": [
    "Real-time analytics",
    "Custom dashboards",
    "AI insights"
  ]
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "E-Commerce Platform",
  "description": "A full-featured e-commerce platform",
  "mode": "student",
  "status": "draft",
  "progress": 0,
  "current_agent": null,
  "total_tokens": 0,
  "total_cost": 0,
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T10:00:00Z",
  "completed_at": null
}
```

### List Projects

```http
GET /projects?page=1&page_size=10
```

**Response:** `200 OK`
```json
{
  "projects": [
    {
      "id": "uuid",
      "title": "E-Commerce Platform",
      "mode": "student",
      "status": "completed",
      "progress": 100,
      "created_at": "2025-01-20T10:00:00Z"
    }
  ],
  "total": 15,
  "page": 1,
  "page_size": 10
}
```

### Get Project

```http
GET /projects/{project_id}
```

**Response:** `200 OK`
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "E-Commerce Platform",
  "description": "A full-featured e-commerce platform",
  "mode": "student",
  "status": "completed",
  "progress": 100,
  "current_agent": null,
  "total_tokens": 15000,
  "total_cost": 1250,
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T11:30:00Z",
  "completed_at": "2025-01-20T11:30:00Z"
}
```

### Execute Project

```http
POST /projects/{project_id}/execute
```

**Response:** `200 OK`
```json
{
  "message": "Project execution started",
  "project_id": "uuid"
}
```

### Delete Project

```http
DELETE /projects/{project_id}
```

**Response:** `204 No Content`

## API Keys

### Create API Key

```http
POST /api-keys
```

**Request Body:**
```json
{
  "name": "Production API Key",
  "description": "API key for production integration"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "name": "Production API Key",
  "key": "bb_abc123xyz...",
  "secret": "secret_abc123xyz..."
}
```

**Note:** The secret is only shown once upon creation. Store it securely!

### List API Keys

```http
GET /api-keys
```

**Response:** `200 OK`
```json
{
  "keys": [
    {
      "id": "uuid",
      "name": "Production API Key",
      "key": "bb_abc123xyz...",
      "status": "active",
      "created_at": "2025-01-20T10:00:00Z",
      "last_used_at": "2025-01-20T15:30:00Z"
    }
  ]
}
```

## Billing

### Get Plans

```http
GET /billing/plans
```

**Response:** `200 OK`
```json
{
  "plans": [
    {
      "name": "Free",
      "price": 0,
      "features": ["1000 tokens/month", "Basic support"]
    },
    {
      "name": "Pro",
      "price": 999,
      "features": ["100K tokens/month", "Priority support", "All modes"]
    },
    {
      "name": "Enterprise",
      "price": 4999,
      "features": ["Unlimited tokens", "Dedicated support", "Custom integrations"]
    }
  ]
}
```

### Get Usage

```http
GET /billing/usage
```

**Response:** `200 OK`
```json
{
  "user_id": "uuid",
  "current_period": {
    "start": "2025-01-01T00:00:00Z",
    "end": "2025-01-31T23:59:59Z"
  },
  "tokens_used": 15000,
  "tokens_limit": 100000,
  "tokens_remaining": 85000,
  "projects_created": 5,
  "total_cost": 12500
}
```

## Using API Keys (Partner Mode)

For API partners, use your API key instead of JWT tokens:

```http
POST /api/v1/projects
X-API-Key: bb_abc123xyz...
X-API-Secret: secret_abc123xyz...
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "detail": "Invalid request parameters"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

API requests are rate-limited based on your plan:

- **Free:** 60 requests/minute, 1000 requests/hour
- **Pro:** 120 requests/minute, 5000 requests/hour
- **Enterprise:** Custom limits

Rate limit headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1642684800
```

## Webhooks

Configure webhooks to receive real-time updates:

### Project Status Updates

```json
{
  "event": "project.status_changed",
  "data": {
    "project_id": "uuid",
    "old_status": "processing",
    "new_status": "completed",
    "timestamp": "2025-01-20T11:30:00Z"
  }
}
```

### Payment Events

```json
{
  "event": "payment.succeeded",
  "data": {
    "transaction_id": "uuid",
    "amount": 999,
    "currency": "INR",
    "timestamp": "2025-01-20T10:00:00Z"
  }
}
```

## SDKs

Official SDKs available for:
- Python
- JavaScript/TypeScript
- Go
- Java

Example (Python):
```python
from bharatbuild import BharatBuildClient

client = BharatBuildClient(api_key="bb_abc123xyz...", secret="secret_abc123xyz...")

project = client.projects.create(
    title="My Project",
    mode="student",
    description="Project description"
)

print(project.id)
```

## Support

For API support:
- Documentation: https://docs.bharatbuild.ai
- Email: api-support@bharatbuild.ai
- Discord: https://discord.gg/bharatbuild
