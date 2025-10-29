"""
Pytest configuration and shared fixtures for GabeDA Backend tests
"""
import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from apps.accounts.models import Company, CompanyMember

User = get_user_model()


@pytest.fixture
def api_client():
    """Return DRF API client"""
    return APIClient()


@pytest.fixture
def user_data():
    """Sample user data for registration"""
    return {
        'email': 'testuser@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'password': 'TestPassword123!',
        'password2': 'TestPassword123!'
    }


@pytest.fixture
def create_user(db):
    """Factory fixture to create users"""
    def make_user(email='user@example.com', password='password123', **kwargs):
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=kwargs.get('first_name', 'Test'),
            last_name=kwargs.get('last_name', 'User')
        )
    return make_user


@pytest.fixture
def user(create_user):
    """Create a test user"""
    return create_user()


@pytest.fixture
def admin_user(create_user):
    """Create an admin user"""
    user = create_user(email='admin@example.com')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    return user


@pytest.fixture
def authenticated_client(api_client, user):
    """Return API client authenticated with test user"""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def company_data():
    """Sample company data"""
    return {
        'name': 'Test Company',
        'industry': 'retail',
        'location': 'Santiago, Chile',
        'currency': 'CLP',
        'top_products_threshold': 0.20,
        'dead_stock_days': 30,
        'column_config': {
            'date_col': 'fecha',
            'product_col': 'producto',
            'description_col': 'glosa',
            'revenue_col': 'total',
            'quantity_col': 'cantidad',
            'transaction_col': 'trans_id'
        }
    }


@pytest.fixture
def create_company(db):
    """Factory fixture to create companies"""
    def make_company(created_by, **kwargs):
        company = Company.objects.create(
            name=kwargs.get('name', 'Test Company'),
            industry=kwargs.get('industry', 'retail'),
            location=kwargs.get('location', 'Santiago, Chile'),
            currency=kwargs.get('currency', 'CLP'),
            created_by=created_by,
            **{k: v for k, v in kwargs.items() if k not in ['name', 'industry', 'location', 'currency']}
        )
        return company
    return make_company


@pytest.fixture
def company(create_company, user):
    """Create a test company"""
    return create_company(created_by=user)


@pytest.fixture
def company_with_admin(company, user):
    """Create a company with user as admin member"""
    CompanyMember.objects.create(
        company=company,
        user=user,
        role='admin'
    )
    return company


@pytest.fixture
def company_with_analyst(company, user):
    """Create a company with user as analyst member"""
    CompanyMember.objects.create(
        company=company,
        user=user,
        role='analyst'
    )
    return company


@pytest.fixture
def get_tokens(api_client, user):
    """Get JWT tokens for a user"""
    def _get_tokens(email=None, password='password123'):
        response = api_client.post('/api/accounts/auth/login/', {
            'email': email or user.email,
            'password': password
        })
        if response.status_code == 200:
            return response.data
        return None
    return _get_tokens
