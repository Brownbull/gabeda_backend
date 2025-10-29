# GabeDA Backend - Django REST API

Business Intelligence backend for GabeDA web application.

## Quick Start

### Prerequisites
- Python 3.11+
- Redis (Docker or WSL2)
- Git

### Setup

```bash
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Run Celery Worker

```bash
# Terminal 2
celery -A config worker -l info
```

## Project Structure

```
gabeda_backend/
├── apps/
│   ├── accounts/      # Authentication, Users, Companies
│   ├── analytics/     # Data Upload, Datasets, Analytics API
│   └── common/        # Shared utilities
├── config/            # Django project settings
│   └── settings/
│       ├── base.py    # Shared settings
│       ├── local.py   # SQLite, DEBUG=True
│       └── production.py  # PostgreSQL, DEBUG=False
├── media/             # User uploads (CSV files)
├── static/            # Static files
├── logs/              # Application logs
└── manage.py
```

## API Endpoints

### Authentication
- `POST /api/auth/register/` - Register new user
- `POST /api/auth/login/` - Login user (get JWT token)
- `POST /api/auth/logout/` - Logout user

### Companies
- `GET /api/companies/` - List user's companies
- `POST /api/companies/` - Create new company
- `GET /api/companies/{id}/` - Get company details
- `PATCH /api/companies/{id}/` - Update company
- `POST /api/companies/{id}/invite/` - Invite user to company

### Data Upload
- `POST /api/companies/{id}/upload/` - Upload CSV file
- `GET /api/companies/{id}/uploads/` - List uploads
- `GET /api/uploads/{id}/status/` - Get upload status

### Dashboards (Role-based)
- `GET /api/companies/{id}/dashboard/kpis/` - Key metrics
- `GET /api/companies/{id}/dashboard/alerts/` - Business alerts
- `GET /api/companies/{id}/dashboard/products/top/` - Top products
- `GET /api/companies/{id}/dashboard/inventory/` - Inventory health
- `GET /api/companies/{id}/dashboard/peak-times/` - Peak sales times

### Export
- `GET /api/companies/{id}/export/excel/` - Export to Excel

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black apps/
```

### Linting
```bash
flake8 apps/
```

## Deployment

See [Windows Setup Guide](https://github.com/yourorg/khujta_ai_business/blob/main/ai/architect/windows_setup_guide.md) for local development.

For cloud deployment (Railway.app), see deployment guide (coming soon).

## Documentation

- [Requirements](https://github.com/yourorg/khujta_ai_business/blob/main/ai/executive/requirements_backend_mvp.md)
- [Technical Design](https://github.com/yourorg/khujta_ai_business/blob/main/ai/architect/backend_technical_design.md)
- [Integration Analysis](https://github.com/yourorg/khujta_ai_business/blob/main/ai/architect/integration_analysis.md)

## License

Proprietary - GabeDA Project
