# Setup Instructions - Quick Start

## ✅ What's Already Done
- ✅ Django project created
- ✅ Apps created (accounts, analytics, common)
- ✅ Settings configured (split: base, local, production)
- ✅ Celery configured
- ✅ .env file created
- ✅ Requirements updated
- ✅ Custom User model created (email-based authentication)
- ✅ Company and CompanyMember models created (multi-tenancy)
- ✅ Database migrated successfully
- ✅ Django configuration verified (no issues)

## 🚀 Next Steps

### 1. Create Superuser
```cmd
python manage.py createsuperuser
```
Enter:
- Email: admin@gabeda.com
- First name: Admin
- Last name: User
- Password: (your choice, min 8 characters)

### 2. Test Server
```cmd
python manage.py runserver
```

Open: http://127.0.0.1:8000/admin

### 3. Test Celery (in separate terminal)
```cmd
cd C:\Projects\play\gabeda_backend
benv\Scripts\activate
celery -A config worker -l info
```

## 🔍 Verify Setup

Run these commands to verify everything is working:

```cmd
REM Check Django
python manage.py check

REM Check GabeDA path is accessible
python -c "import sys; sys.path.insert(0, 'C:/Projects/play/khujta_ai_business'); from src.core.context import GabedaContext; print('[OK] GabeDA import successful')"

REM Run tests
pytest
```

## 📝 What's Next?

After creating the superuser, we'll continue with:
1. DataUpload and Transaction models (Week 3)
2. Authentication API endpoints (register, login, logout)
3. CSV upload endpoint
4. Dataset generation service (integrate with GabeDA /src)
5. Analytics API endpoints
6. Basic tests

## ⚠️ Troubleshooting

**If you see "No module named 'django'":**
- Make sure virtual environment is activated: `benv\Scripts\activate`

**If settings.py conflicts:**
- Delete `config\settings.py`: `del config\settings.py`
- We're using `config\settings\local.py` now

**If Redis connection fails:**
- Make sure Redis is running (Docker or WSL2)
- Test: `redis-cli ping` (should return PONG)
