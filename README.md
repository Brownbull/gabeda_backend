# GabeDA Backend

Django REST API backend for the GabeDA Business Intelligence platform.

## Overview

Multi-tenant Django backend with JWT authentication, role-based access control, CSV upload functionality, and integration with the GabeDA analytics engine.

### Key Features

- Multi-Tenant Architecture with complete data isolation
- JWT Authentication (djangorestframework-simplejwt)
- Role-Based Access Control (Admin, Business Owner, Analyst, Operations Manager)
- CSV Upload and automated analytics generation
- RESTful API with comprehensive documentation
- Django Admin interface for data management

## Quick Start

### Prerequisites
- Python 3.10+ (currently using 3.12)
- Virtual environment: `benv` (already created)
- Redis (optional, for Celery background tasks)

### Run Development Server

```cmd
cd C:\Projects\play\gabeda_backend
benv\Scripts\activate
python manage.py runserver
```

**Access:**
- API: http://127.0.0.1:8000/api
- Admin: http://127.0.0.1:8000/admin

### Create Superuser

```cmd
python manage.py createsuperuser
```

Enter:
- Email: admin@gabeda.com
- First name: Admin
- Last name: User
- Password: (your choice, min 8 characters)

### Test API

```cmd
python test_api.py
```

## Database Models

### Accounts App (7 models total)
- **User** - Email-based authentication, UUID primary keys
- **Company** - Multi-tenant companies with JSON column_config
- **CompanyMember** - User-company relationships with RBAC roles

### Analytics App (4 models total)
- **DataUpload** - Track CSV uploads and processing status
- **Transaction** - Individual transaction records (multi-tenant)
- **Dataset** - Generated datasets from GabeDA pipeline
- **AnalyticsResult** - KPIs, insights, alerts (role-based visibility)

## API Endpoints

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete reference.

### Authentication
- `POST /api/accounts/auth/register/` - Register new user
- `POST /api/accounts/auth/login/` - Login (get JWT tokens)
- `POST /api/accounts/auth/token/refresh/` - Refresh access token

### User Profile
- `GET /api/accounts/profile/` - Get current user profile
- `PUT /api/accounts/profile/` - Update profile

### Companies
- `GET /api/accounts/companies/` - List user's companies
- `POST /api/accounts/companies/` - Create company (auto-adds creator as admin)
- `GET /api/accounts/companies/{id}/` - Get company details
- `PUT /api/accounts/companies/{id}/` - Update company
- `DELETE /api/accounts/companies/{id}/` - Delete company
- `GET /api/accounts/companies/{id}/members/` - List company members
- `POST /api/accounts/companies/{id}/add_member/` - Add member (admin only)
- `DELETE /api/accounts/companies/{id}/remove_member/` - Remove member (admin only)

### Memberships
- `GET /api/accounts/memberships/` - List user's company memberships

### Analytics (Coming Soon)
- CSV upload endpoint
- Dataset retrieval
- Analytics results
- Export to Excel/PDF

## What's Implemented

### ✅ Completed (Phase 1 - Week 1-2)
- Django project setup with split settings (base, local, production)
- Custom User model (email-based authentication)
- Company and CompanyMember models (multi-tenancy + RBAC)
- DataUpload, Transaction, Dataset, AnalyticsResult models
- Authentication API (register, login, token refresh)
- Company management API (CRUD + member management)
- User profile API
- Django Admin for all models
- JWT authentication configured
- GabeDA /src integration path configured
- API test script (test_api.py)
- Complete API documentation (API_DOCUMENTATION.md)

### ⏳ In Progress (Phase 1 - Week 3)
- CSV upload endpoint with validation
- DatasetGenerationService (bridge to GabeDA /src)
- Celery tasks for background processing

### 📋 Upcoming (Phase 1 - Week 4-6)
- Analytics API endpoints
- Dataset retrieval endpoints
- Role-based analytics filtering
- Excel/PDF export
- Basic API tests (pytest)

## Next Steps

To continue with development:

1. **Test Current API**: Run `python test_api.py` to verify authentication and company endpoints
2. **Create CSV Upload Endpoint**: Implement file upload with validation
3. **Build DatasetGenerationService**: Integrate with GabeDA `/src` analytics engine
4. **Add Celery Tasks**: Background processing for dataset generation
5. **Create Analytics API**: Endpoints for retrieving KPIs, alerts, insights
6. **Write Tests**: Comprehensive pytest suite

## Documentation

- [API_DOCUMENTATION.md](API_DOCUMENTATION.md) - Complete API reference
- [test_api.py](test_api.py) - API usage examples
- [../khujta_ai_business/ai/executive/requirements_backend_mvp.md](../khujta_ai_business/ai/executive/requirements_backend_mvp.md) - MVP requirements
- [../khujta_ai_business/ai/architect/backend_technical_design.md](../khujta_ai_business/ai/architect/backend_technical_design.md) - Technical design
- [../khujta_ai_business/ai/architect/integration_analysis.md](../khujta_ai_business/ai/architect/integration_analysis.md) - GabeDA integration strategy

## Support

**Verify Setup:**
```cmd
python manage.py check  # Should return: System check identified no issues
python manage.py runserver  # Start development server
python test_api.py  # Test authentication flow
```

**Access Admin:**
http://127.0.0.1:8000/admin

**Access API:**
http://127.0.0.1:8000/api/accounts/

## License

Proprietary - GabeDA Business Intelligence Platform
