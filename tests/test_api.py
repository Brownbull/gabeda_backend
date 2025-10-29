"""
Quick API Test Script
=====================

This script demonstrates how to use the GabeDA API endpoints.

Run Django server first:
    python manage.py runserver

Then run this script in a separate terminal:
    python test_api.py
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

def print_response(title, response):
    """Pretty print API response"""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}")
    print(f"Status Code: {response.status_code}")
    try:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Response: {response.text}")


def test_authentication():
    """Test authentication flow"""

    # 1. Register a new user
    print("\n\n1. REGISTERING NEW USER")
    print("-" * 60)
    register_data = {
        "email": "test@gabeda.com",
        "first_name": "Test",
        "last_name": "User",
        "password": "TestPassword123!",
        "password2": "TestPassword123!"
    }
    response = requests.post(f"{BASE_URL}/accounts/auth/register/", json=register_data)
    print_response("Register Response", response)

    # 2. Login
    print("\n\n2. LOGGING IN")
    print("-" * 60)
    login_data = {
        "email": "test@gabeda.com",
        "password": "TestPassword123!"
    }
    response = requests.post(f"{BASE_URL}/accounts/auth/login/", json=login_data)
    print_response("Login Response", response)

    if response.status_code == 200:
        tokens = response.json()
        access_token = tokens.get('access')
        refresh_token = tokens.get('refresh')

        # 3. Get user profile
        print("\n\n3. GETTING USER PROFILE")
        print("-" * 60)
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(f"{BASE_URL}/accounts/profile/", headers=headers)
        print_response("Profile Response", response)

        # 4. Create a company
        print("\n\n4. CREATING A COMPANY")
        print("-" * 60)
        company_data = {
            "name": "Test Company",
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
        response = requests.post(f"{BASE_URL}/accounts/companies/", json=company_data, headers=headers)
        print_response("Create Company Response", response)

        if response.status_code == 201:
            company = response.json()
            company_id = company.get('id')

            # 5. List companies
            print("\n\n5. LISTING COMPANIES")
            print("-" * 60)
            response = requests.get(f"{BASE_URL}/accounts/companies/", headers=headers)
            print_response("Companies List Response", response)

            # 6. Get company members
            print("\n\n6. GETTING COMPANY MEMBERS")
            print("-" * 60)
            response = requests.get(f"{BASE_URL}/accounts/companies/{company_id}/members/", headers=headers)
            print_response("Company Members Response", response)

            # 7. Get user memberships
            print("\n\n7. GETTING USER MEMBERSHIPS")
            print("-" * 60)
            response = requests.get(f"{BASE_URL}/accounts/memberships/", headers=headers)
            print_response("User Memberships Response", response)

        # 8. Refresh token
        print("\n\n8. REFRESHING TOKEN")
        print("-" * 60)
        refresh_data = {"refresh": refresh_token}
        response = requests.post(f"{BASE_URL}/accounts/auth/token/refresh/", json=refresh_data)
        print_response("Token Refresh Response", response)


def test_api_documentation():
    """List all available endpoints"""
    print("\n\n" + "="*60)
    print("AVAILABLE API ENDPOINTS")
    print("="*60)

    endpoints = {
        "Authentication": [
            "POST /api/accounts/auth/register/ - Register new user",
            "POST /api/accounts/auth/login/ - Login (get JWT tokens)",
            "POST /api/accounts/auth/token/refresh/ - Refresh access token"
        ],
        "User Profile": [
            "GET /api/accounts/profile/ - Get current user profile",
            "PUT /api/accounts/profile/ - Update current user profile",
            "PATCH /api/accounts/profile/ - Partial update profile"
        ],
        "Companies": [
            "GET /api/accounts/companies/ - List user's companies",
            "POST /api/accounts/companies/ - Create new company",
            "GET /api/accounts/companies/{id}/ - Get company details",
            "PUT /api/accounts/companies/{id}/ - Update company",
            "DELETE /api/accounts/companies/{id}/ - Delete company",
            "GET /api/accounts/companies/{id}/members/ - List company members",
            "POST /api/accounts/companies/{id}/add_member/ - Add member to company",
            "DELETE /api/accounts/companies/{id}/remove_member/ - Remove member"
        ],
        "Memberships": [
            "GET /api/accounts/memberships/ - List user's company memberships"
        ]
    }

    for category, urls in endpoints.items():
        print(f"\n{category}:")
        for url in urls:
            print(f"  - {url}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("GABEDA API TEST SCRIPT")
    print("="*60)
    print("\nMake sure Django server is running:")
    print("  python manage.py runserver")
    print("\n")

    try:
        # Test if server is running
        response = requests.get("http://127.0.0.1:8000/admin/", timeout=2)
        print("[OK] Django server is running!")

        # Show available endpoints
        test_api_documentation()

        # Run authentication tests
        test_authentication()

        print("\n\n" + "="*60)
        print("TESTS COMPLETED!")
        print("="*60)

    except requests.exceptions.ConnectionError:
        print("[ERROR] Django server is not running!")
        print("\nPlease start the server first:")
        print("  cd C:\\Projects\\play\\gabeda_backend")
        print("  benv\\Scripts\\activate")
        print("  python manage.py runserver")
