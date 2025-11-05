"""Debug script for company filtering test"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')
django.setup()

from apps.accounts.models import User, Company, CompanyMember
from apps.analytics.models import DataUpload
from rest_framework.test import APIClient

# Create test data
user = User.objects.create_user(email='test@example.com', password='password123')
company = Company.objects.create(
    name='Test Company',
    industry='retail',
    location='Santiago',
    currency='CLP',
    created_by=user
)
CompanyMember.objects.get_or_create(company=company, user=user, defaults={'role': 'admin'})

data_upload = DataUpload.objects.create(
    company=company,
    uploaded_by=user,
    file_name='test.csv',
    file_size=1024,
    file_path='uploads/test.csv',
    status='completed',
    row_count=100
)

# Test the endpoint
client = APIClient()
client.force_authenticate(user=user)
response = client.get(f'/api/analytics/uploads/by_company/?company_id={company.id}')

print(f"Status: {response.status_code}")
print(f"Company ID: {company.id}")
print(f"Response data: {response.data}")

# Check what's in results
if isinstance(response.data, dict) and 'results' in response.data:
    results = response.data['results']
else:
    results = response.data

print(f"\nNumber of results: {len(results)}")
for idx, upload in enumerate(results):
    print(f"Upload {idx+1}: company={upload.get('company')}, file_name={upload.get('file_name')}")
    print(f"  Match: {upload.get('company') == str(company.id)}")
