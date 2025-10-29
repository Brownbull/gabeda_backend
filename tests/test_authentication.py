"""
Test suite for authentication endpoints
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework import status

User = get_user_model()

pytestmark = [pytest.mark.auth, pytest.mark.django_db]


class TestUserRegistration:
    """Test user registration endpoint"""

    def test_register_user_success(self, api_client, user_data):
        """Test successful user registration"""
        response = api_client.post('/api/accounts/auth/register/', user_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert 'user' in response.data
        assert 'message' in response.data
        assert response.data['user']['email'] == user_data['email']
        assert response.data['user']['first_name'] == user_data['first_name']
        assert response.data['user']['last_name'] == user_data['last_name']

        # Verify user was created in database
        assert User.objects.filter(email=user_data['email']).exists()

    def test_register_user_duplicate_email(self, api_client, user_data, user):
        """Test registration with existing email fails"""
        user_data['email'] = user.email

        response = api_client.post('/api/accounts/auth/register/', user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_user_password_mismatch(self, api_client, user_data):
        """Test registration fails when passwords don't match"""
        user_data['password2'] = 'DifferentPassword123!'

        response = api_client.post('/api/accounts/auth/register/', user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in response.data

    def test_register_user_weak_password(self, api_client, user_data):
        """Test registration fails with weak password"""
        user_data['password'] = '123'
        user_data['password2'] = '123'

        response = api_client.post('/api/accounts/auth/register/', user_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_user_missing_fields(self, api_client):
        """Test registration fails with missing required fields"""
        response = api_client.post('/api/accounts/auth/register/', {
            'email': 'test@example.com'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'first_name' in response.data or 'password' in response.data


class TestUserLogin:
    """Test user login endpoint"""

    def test_login_success(self, api_client, user):
        """Test successful login returns JWT tokens"""
        response = api_client.post('/api/accounts/auth/login/', {
            'email': user.email,
            'password': 'password123'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert len(response.data['access']) > 0
        assert len(response.data['refresh']) > 0

    def test_login_wrong_password(self, api_client, user):
        """Test login fails with wrong password"""
        response = api_client.post('/api/accounts/auth/login/', {
            'email': user.email,
            'password': 'wrongpassword'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login fails for non-existent user"""
        response = api_client.post('/api/accounts/auth/login/', {
            'email': 'nonexistent@example.com',
            'password': 'password123'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_credentials(self, api_client):
        """Test login fails with missing credentials"""
        response = api_client.post('/api/accounts/auth/login/', {
            'email': 'test@example.com'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestTokenRefresh:
    """Test token refresh endpoint"""

    def test_refresh_token_success(self, api_client, user, get_tokens):
        """Test successful token refresh"""
        tokens = get_tokens(user.email)
        assert tokens is not None

        response = api_client.post('/api/accounts/auth/token/refresh/', {
            'refresh': tokens['refresh']
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert len(response.data['access']) > 0

    def test_refresh_token_invalid(self, api_client):
        """Test token refresh fails with invalid token"""
        response = api_client.post('/api/accounts/auth/token/refresh/', {
            'refresh': 'invalid_token'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestUserProfile:
    """Test user profile endpoints"""

    def test_get_profile_authenticated(self, authenticated_client, user):
        """Test authenticated user can get their profile"""
        response = authenticated_client.get('/api/accounts/profile/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user.email
        assert response.data['first_name'] == user.first_name
        assert response.data['last_name'] == user.last_name

    def test_get_profile_unauthenticated(self, api_client):
        """Test unauthenticated user cannot get profile"""
        response = api_client.get('/api/accounts/profile/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile_success(self, authenticated_client, user):
        """Test authenticated user can update their profile"""
        response = authenticated_client.patch('/api/accounts/profile/', {
            'first_name': 'Updated',
            'last_name': 'Name'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == 'Updated'
        assert response.data['last_name'] == 'Name'

        # Verify in database
        user.refresh_from_db()
        assert user.first_name == 'Updated'
        assert user.last_name == 'Name'

    def test_update_profile_readonly_fields(self, authenticated_client, user):
        """Test readonly fields cannot be updated"""
        original_email = user.email
        response = authenticated_client.patch('/api/accounts/profile/', {
            'email': 'newemail@example.com',
            'id': 'some-uuid'
        })

        # Email should remain unchanged
        user.refresh_from_db()
        assert user.email == original_email
