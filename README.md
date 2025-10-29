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

See [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) for complete reference.

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

### ✅ Completed (Phase 1 - Backend MVP)
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
- **CSV upload endpoint with validation** ✅
- **DatasetGenerationService (bridge to GabeDA /src)** ✅
- **Comprehensive test suite (71 tests, 90% passing)** ✅
- Complete API documentation (docs/API_DOCUMENTATION.md)
- Test results documentation (docs/BACKEND_TEST_RESULTS.md)

### 📋 Upcoming (Phase 2 - Frontend & Polish)
- **Frontend web application** (React/Next.js recommended)
- Celery tasks for async background processing
- Analytics API endpoints (currently returns mock data)
- Dataset retrieval endpoints
- Role-based analytics filtering refinement
- Excel/PDF export improvements
- Fix remaining 6 failing tests

## Project Structure

```
gabeda_backend/
├── apps/                 # Django applications
│   ├── accounts/        # User, Company, CompanyMember models
│   └── analytics/       # DataUpload, Transaction, Dataset, AnalyticsResult
├── config/              # Django settings
│   └── settings/        # Split settings (base, local, production)
├── docs/                # Documentation
│   ├── API_DOCUMENTATION.md
│   ├── BACKEND_TEST_RESULTS.md
│   └── SETUP_INSTRUCTIONS.md
├── scripts/             # Utility scripts
│   └── setup_apps.py   # App creation script
├── tests/               # Test suite (71 tests)
│   ├── conftest.py     # Pytest fixtures
│   ├── test_authentication.py
│   ├── test_companies.py
│   ├── test_analytics.py
│   └── test_dataset_generation.py
├── media/               # Uploaded files (gitignored)
├── static/              # Static files
├── logs/                # Application logs
├── manage.py           # Django management
├── pytest.ini          # Pytest configuration
└── requirements.txt    # Python dependencies
```

## Next Steps

### Option 1: Build Frontend Application 🎨

Create a React/Next.js frontend to interact with the backend API:

**Recommended Tech Stack:**
- **Framework**: Next.js 14+ (App Router)
- **UI Library**: shadcn/ui + Tailwind CSS
- **State Management**: React Context or Zustand
- **API Client**: Axios or fetch with SWR
- **Auth**: JWT token management with refresh
- **Charts**: Recharts or Chart.js

**Key Features to Implement:**
1. **Authentication Pages**
   - Login/Register forms
   - JWT token storage (localStorage + httpOnly cookies)
   - Protected routes

2. **Dashboard**
   - Company selection
   - CSV upload interface
   - Analytics results display (KPIs, charts)

3. **Company Management**
   - Create/edit companies
   - Manage team members
   - Role assignment

4. **Analytics Views**
   - Upload history
   - Transaction data tables
   - Interactive charts (revenue, pareto, trends)

### Option 2: Backend Improvements 🔧

Continue refining the backend:

1. **Fix Remaining Tests** (6 failing tests)
   - Filter assertions in analytics endpoints
   - Company creation validation
   - Profile readonly fields

2. **Implement Celery for Async Processing**
   - Move DatasetGenerationService to background tasks
   - Add progress tracking
   - Email notifications on completion

3. **Enhance GabeDA Integration**
   - Replace mock results with actual GabeDA pipeline
   - Implement `_extract_kpis()`, `_extract_alerts()`, etc.
   - Add Dataset metadata scanning

4. **Add More API Features**
   - Filtering and pagination improvements
   - Bulk operations
   - Export to Excel/PDF endpoints

### Option 3: DevOps & Deployment 🚀

Prepare for production:

1. **Docker Setup**
   - Dockerfile for Django app
   - Docker Compose (Django + PostgreSQL + Redis + Celery)
   - nginx configuration

2. **CI/CD Pipeline**
   - GitHub Actions for testing
   - Automated deployment

3. **Production Database**
   - Migrate from SQLite to PostgreSQL
   - Database migrations strategy

## Documentation

- [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) - Complete API reference
- [docs/BACKEND_TEST_RESULTS.md](docs/BACKEND_TEST_RESULTS.md) - Test suite results
- [docs/SETUP_INSTRUCTIONS.md](docs/SETUP_INSTRUCTIONS.md) - Setup guide
- [../khujta_ai_business/ai/executive/requirements_backend_mvp.md](../khujta_ai_business/ai/executive/requirements_backend_mvp.md) - MVP requirements
- [../khujta_ai_business/ai/architect/backend_technical_design.md](../khujta_ai_business/ai/architect/backend_technical_design.md) - Technical design

## Running Tests

```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_dataset_generation.py -v

# With coverage
pytest tests/ --cov=apps --cov-report=html

# Only failures
pytest tests/ --lf
```

**Current Status**: 64/71 tests passing (90.1%)

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
