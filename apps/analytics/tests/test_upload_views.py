"""
Unit tests for DataUpload API endpoints
Tests API response format consistency (POST and GET)
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.accounts.models import Company, CompanyMember
from apps.analytics.models import DataUpload
import io

User = get_user_model()


class DataUploadAPIResponseFormatTests(TestCase):
    """Test DataUpload API response formats for consistency"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()

        # Create test user
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Create test company
        self.company = Company.objects.create(
            name='Test Company',
            created_by=self.user
        )

        # Add user as company member
        CompanyMember.objects.create(
            company=self.company,
            user=self.user,
            role='admin'
        )

        # Authenticate
        self.client.force_authenticate(user=self.user)

    def _create_test_csv_file(self, filename='test_upload.csv'):
        """Helper to create a valid test CSV file"""
        csv_content = (
            "trans_id,fecha,producto,glosa,cantidad,total\n"
            "1,2025-01-01,SKU001,Product 1,5,100.00\n"
            "2,2025-01-02,SKU002,Product 2,3,75.50\n"
            "3,2025-01-03,SKU001,Product 1,2,40.00\n"
        )
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        csv_file.name = filename
        return csv_file

    def test_upload_create_returns_direct_format(self):
        """
        Test POST /companies/{id}/upload/ returns direct serialization
        CRITICAL: Response should NOT be wrapped in { message: ..., upload: {...} }
        """
        # Create test CSV file
        csv_file = self._create_test_csv_file()

        # Upload file
        response = self.client.post(
            f'/api/analytics/companies/{self.company.id}/upload/',
            {'file': csv_file},
            format='multipart'
        )

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # ✅ Response should be DIRECT serialization (no wrapper)
        self.assertIn('id', response.data, "Response missing 'id' field")
        self.assertIn('status', response.data, "Response missing 'status' field")
        self.assertIn('file_name', response.data, "Response missing 'file_name' field")
        self.assertIn('uploaded_at', response.data, "Response missing 'uploaded_at' field")

        # ❌ Should NOT have wrapper fields
        self.assertNotIn('message', response.data, "Response should not have 'message' wrapper")
        self.assertNotIn('upload', response.data, "Response should not have 'upload' wrapper")

        # Verify upload object structure
        self.assertEqual(response.data['status'], 'pending')
        self.assertEqual(response.data['file_name'], 'test_upload.csv')

        # Verify Location header
        self.assertIn('Location', response)
        self.assertIn(f'/api/analytics/uploads/{response.data["id"]}/', response['Location'])

    def test_upload_retrieve_returns_direct_format(self):
        """
        Test GET /uploads/{id}/ returns direct serialization
        """
        # Create upload directly in database
        upload = DataUpload.objects.create(
            company=self.company,
            uploaded_by=self.user,
            file_name='test.csv',
            file_size=1024,
            file_path='uploads/test/test.csv',
            status='pending'
        )

        # Retrieve upload
        response = self.client.get(f'/api/analytics/uploads/{upload.id}/')

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # ✅ Response should be DIRECT serialization
        self.assertIn('id', response.data)
        self.assertIn('status', response.data)
        self.assertIn('file_name', response.data)
        self.assertIn('uploaded_at', response.data)

        # ❌ Should NOT have wrapper
        self.assertNotIn('upload', response.data, "Response should not have 'upload' wrapper")

    def test_response_format_consistency_between_post_and_get(self):
        """
        Test POST and GET return same format structure
        CRITICAL: Both endpoints should return identical top-level keys
        """
        # Upload file
        csv_file = self._create_test_csv_file('consistency_test.csv')

        create_response = self.client.post(
            f'/api/analytics/companies/{self.company.id}/upload/',
            {'file': csv_file},
            format='multipart'
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        upload_id = create_response.data['id']

        # Retrieve upload
        retrieve_response = self.client.get(
            f'/api/analytics/uploads/{upload_id}/'
        )
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)

        # ✅ Both should have same top-level keys
        create_keys = set(create_response.data.keys())
        retrieve_keys = set(retrieve_response.data.keys())

        # Common required keys (both endpoints must have these)
        required_keys = {'id', 'status', 'file_name', 'uploaded_at', 'company'}
        self.assertTrue(
            required_keys.issubset(create_keys),
            f"POST response missing required keys. Has: {create_keys}, Expected: {required_keys}"
        )
        self.assertTrue(
            required_keys.issubset(retrieve_keys),
            f"GET response missing required keys. Has: {retrieve_keys}, Expected: {required_keys}"
        )

        # Key sets should be identical (exact same structure)
        self.assertEqual(
            create_keys,
            retrieve_keys,
            f"POST and GET responses have different structures.\nPOST: {sorted(create_keys)}\nGET: {sorted(retrieve_keys)}"
        )

    def test_upload_create_with_invalid_file(self):
        """Test upload validation with invalid CSV"""
        # Create file with wrong extension
        invalid_file = io.BytesIO(b"not a csv file")
        invalid_file.name = 'test.txt'

        response = self.client.post(
            f'/api/analytics/companies/{self.company.id}/upload/',
            {'file': invalid_file},
            format='multipart'
        )

        # Should return 400 Bad Request
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # DRF validation errors are nested under field name
        self.assertIn('file', response.data)

    def test_upload_create_without_authentication(self):
        """Test upload requires authentication"""
        # Logout
        self.client.force_authenticate(user=None)

        csv_file = self._create_test_csv_file()

        response = self.client.post(
            f'/api/analytics/companies/{self.company.id}/upload/',
            {'file': csv_file},
            format='multipart'
        )

        # Should return 401 Unauthorized
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_create_without_company_membership(self):
        """Test upload requires company membership"""
        # Create another user (not member of company)
        other_user = User.objects.create_user(
            email='otheruser@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=other_user)

        csv_file = self._create_test_csv_file()

        response = self.client.post(
            f'/api/analytics/companies/{self.company.id}/upload/',
            {'file': csv_file},
            format='multipart'
        )

        # Should return 403 Forbidden
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_upload_list_returns_user_company_uploads(self):
        """Test GET /uploads/ returns only user's company uploads"""
        # Create uploads
        upload1 = DataUpload.objects.create(
            company=self.company,
            uploaded_by=self.user,
            file_name='upload1.csv',
            file_size=1024,
            file_path='uploads/test/upload1.csv',
            status='completed'
        )

        upload2 = DataUpload.objects.create(
            company=self.company,
            uploaded_by=self.user,
            file_name='upload2.csv',
            file_size=2048,
            file_path='uploads/test/upload2.csv',
            status='pending'
        )

        # Create another company and upload (should not appear)
        other_company = Company.objects.create(
            name='Other Company',
            created_by=self.user
        )
        other_upload = DataUpload.objects.create(
            company=other_company,
            uploaded_by=self.user,
            file_name='other.csv',
            file_size=512,
            file_path='uploads/other/other.csv',
            status='pending'
        )

        # List uploads (should only see company's uploads if not member of other_company)
        response = self.client.get('/api/analytics/uploads/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handle both paginated and non-paginated responses
        if isinstance(response.data, dict) and 'results' in response.data:
            # Paginated response
            results = response.data['results']
        else:
            # Non-paginated response
            results = response.data

        # Verify correct uploads returned
        upload_ids = [item['id'] for item in results]
        self.assertIn(str(upload1.id), upload_ids)
        self.assertIn(str(upload2.id), upload_ids)

    def test_superuser_can_see_all_uploads(self):
        """Test superuser can access all uploads"""
        # Create superuser
        superuser = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass123'
        )
        self.client.force_authenticate(user=superuser)

        # Create upload
        upload = DataUpload.objects.create(
            company=self.company,
            uploaded_by=self.user,
            file_name='test.csv',
            file_size=1024,
            file_path='uploads/test/test.csv',
            status='pending'
        )

        # Superuser should be able to retrieve any upload
        response = self.client.get(f'/api/analytics/uploads/{upload.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(upload.id))


class DataUploadSerializerTests(TestCase):
    """Test DataUpload serializer behavior"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='testuser@example.com',
            password='testpass123'
        )
        self.company = Company.objects.create(
            name='Test Company',
            created_by=self.user
        )

    def test_serializer_output_structure(self):
        """Test serializer produces expected output structure"""
        from apps.analytics.serializers import DataUploadSerializer

        upload = DataUpload.objects.create(
            company=self.company,
            uploaded_by=self.user,
            file_name='test.csv',
            file_size=1024,
            file_path='uploads/test/test.csv',
            status='pending'
        )

        serializer = DataUploadSerializer(upload)
        data = serializer.data

        # Required fields
        required_fields = [
            'id', 'company', 'uploaded_by', 'file_name',
            'file_size', 'status', 'uploaded_at'
        ]

        for field in required_fields:
            self.assertIn(field, data, f"Serializer missing required field: {field}")

        # Verify data types
        self.assertIsInstance(data['id'], str)  # UUID as string
        self.assertEqual(data['status'], 'pending')
        self.assertEqual(data['file_name'], 'test.csv')
        self.assertEqual(data['file_size'], 1024)
