"""
Test suite for analytics endpoints
"""
import pytest
import io
from rest_framework import status
from conftest import get_results
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.analytics.models import DataUpload, Transaction, Dataset, AnalyticsResult

pytestmark = [pytest.mark.analytics, pytest.mark.django_db]


@pytest.fixture
def csv_file():
    """Create a sample CSV file for testing"""
    csv_content = b"""trans_id,fecha,producto,glosa,cantidad,total
1,2025-01-15,PROD001,Product 1,10,1000
2,2025-01-15,PROD002,Product 2,5,500
3,2025-01-16,PROD001,Product 1,15,1500
"""
    return SimpleUploadedFile("test_transactions.csv", csv_content, content_type="text/csv")


@pytest.fixture
def invalid_csv_file():
    """Create an invalid file (not CSV)"""
    return SimpleUploadedFile("test.txt", b"not a csv", content_type="text/plain")


@pytest.fixture
def empty_csv_file():
    """Create an empty CSV file"""
    return SimpleUploadedFile("empty.csv", b"", content_type="text/csv")


@pytest.fixture
def data_upload(db, company_with_admin, user):
    """Create a test data upload"""
    return DataUpload.objects.create(
        company=company_with_admin,
        uploaded_by=user,
        file_name='test.csv',
        file_size=1024,
        file_path='uploads/test.csv',
        status='completed',
        row_count=100
    )


class TestCSVUpload:
    """Test CSV file upload endpoint"""

    def test_upload_csv_success(self, authenticated_client, company_with_admin, csv_file):
        """Test successful CSV upload"""
        response = authenticated_client.post(
            f'/api/analytics/companies/{company_with_admin.id}/upload/',
            {'file': csv_file},
            format='multipart'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert 'message' in response.data
        assert 'upload' in response.data

        # Status should be 'completed' since processing is synchronous
        assert response.data['upload']['status'] == 'completed'
        assert 'processing_result' in response.data
        assert response.data['processing_result']['success'] is True

        # Verify DataUpload was created
        upload_id = response.data['upload']['id']
        assert DataUpload.objects.filter(id=upload_id).exists()

    def test_upload_csv_unauthenticated(self, api_client, company_with_admin, csv_file):
        """Test unauthenticated user cannot upload CSV"""
        response = api_client.post(
            f'/api/analytics/companies/{company_with_admin.id}/upload/',
            {'file': csv_file},
            format='multipart'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_upload_csv_non_member(
        self, authenticated_client, create_company, create_user, csv_file
    ):
        """Test non-member cannot upload CSV"""
        other_user = create_user(email='other@example.com')
        other_company = create_company(created_by=other_user)

        response = authenticated_client.post(
            f'/api/analytics/companies/{other_company.id}/upload/',
            {'file': csv_file},
            format='multipart'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_upload_invalid_file_type(
        self, authenticated_client, company_with_admin, invalid_csv_file
    ):
        """Test upload fails with non-CSV file"""
        response = authenticated_client.post(
            f'/api/analytics/companies/{company_with_admin.id}/upload/',
            {'file': invalid_csv_file},
            format='multipart'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'file' in response.data

    def test_upload_empty_file(
        self, authenticated_client, company_with_admin, empty_csv_file
    ):
        """Test upload fails with empty file"""
        response = authenticated_client.post(
            f'/api/analytics/companies/{company_with_admin.id}/upload/',
            {'file': empty_csv_file},
            format='multipart'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_upload_missing_file(self, authenticated_client, company_with_admin):
        """Test upload fails without file"""
        response = authenticated_client.post(
            f'/api/analytics/companies/{company_with_admin.id}/upload/',
            {},
            format='multipart'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestDataUploadList:
    """Test data upload list endpoint"""

    def test_list_uploads_success(self, authenticated_client, data_upload):
        """Test authenticated user can list uploads"""
        response = authenticated_client.get('/api/analytics/uploads/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1
        assert any(u['id'] == str(data_upload.id) for u in results)

    def test_list_uploads_empty(self, authenticated_client):
        """Test user with no uploads sees empty list"""
        response = authenticated_client.get('/api/analytics/uploads/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) == 0

    def test_list_uploads_unauthenticated(self, api_client):
        """Test unauthenticated user cannot list uploads"""
        response = api_client.get('/api/analytics/uploads/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_uploads_by_company(
        self, authenticated_client, company_with_admin, data_upload
    ):
        """Test filtering uploads by company"""
        response = authenticated_client.get(
            f'/api/analytics/uploads/by_company/?company_id={company_with_admin.id}'
        )

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1
        assert all(u['company'] == str(company_with_admin.id) for u in results)


class TestDataUploadDetail:
    """Test data upload detail endpoint"""

    def test_get_upload_detail_success(self, authenticated_client, data_upload):
        """Test member can get upload details"""
        response = authenticated_client.get(f'/api/analytics/uploads/{data_upload.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(data_upload.id)
        assert response.data['file_name'] == data_upload.file_name
        assert response.data['status'] == data_upload.status

    def test_get_upload_detail_non_member(
        self, authenticated_client, create_company, create_user, db
    ):
        """Test non-member cannot get upload details"""
        other_user = create_user(email='other@example.com')
        other_company = create_company(created_by=other_user)
        other_upload = DataUpload.objects.create(
            company=other_company,
            uploaded_by=other_user,
            file_name='other.csv',
            file_size=1024,
            file_path='uploads/other.csv',
            status='pending'
        )

        response = authenticated_client.get(f'/api/analytics/uploads/{other_upload.id}/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTransactionList:
    """Test transaction list endpoint"""

    @pytest.fixture
    def transaction(self, db, company_with_admin, data_upload):
        """Create a test transaction"""
        return Transaction.objects.create(
            company=company_with_admin,
            upload=data_upload,
            transaction_id='T001',
            date='2025-01-15',
            product_id='P001',
            product_description='Test Product',
            quantity=10,
            unit_price=100,
            total=1000
        )

    def test_list_transactions_success(self, authenticated_client, transaction):
        """Test authenticated user can list transactions"""
        response = authenticated_client.get('/api/analytics/transactions/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1
        assert any(t['id'] == str(transaction.id) for t in results)

    def test_list_transactions_filter_by_company(
        self, authenticated_client, transaction, company_with_admin
    ):
        """Test filtering transactions by company"""
        response = authenticated_client.get(
            f'/api/analytics/transactions/?company_id={company_with_admin.id}'
        )

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert all(t['company'] == str(company_with_admin.id) for t in results)

    def test_list_transactions_filter_by_date_range(self, authenticated_client, transaction):
        """Test filtering transactions by date range"""
        response = authenticated_client.get(
            '/api/analytics/transactions/?start_date=2025-01-01&end_date=2025-01-31'
        )

        assert response.status_code == status.HTTP_200_OK


class TestDatasetList:
    """Test dataset list endpoint"""

    @pytest.fixture
    def dataset(self, db, company_with_admin, data_upload):
        """Create a test dataset"""
        return Dataset.objects.create(
            company=company_with_admin,
            upload=data_upload,
            name='Test Dataset',
            dataset_type='filtered',
            file_path='datasets/test.csv',
            row_count=100
        )

    def test_list_datasets_success(self, authenticated_client, dataset):
        """Test authenticated user can list datasets"""
        response = authenticated_client.get('/api/analytics/datasets/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1
        assert any(d['id'] == str(dataset.id) for d in results)

    def test_list_datasets_filter_by_type(self, authenticated_client, dataset):
        """Test filtering datasets by type"""
        response = authenticated_client.get(
            '/api/analytics/datasets/?dataset_type=filtered'
        )

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert all(d['dataset_type'] == 'filtered' for d in results)


class TestAnalyticsResults:
    """Test analytics results endpoint"""

    @pytest.fixture
    def kpi_result(self, db, company_with_admin, data_upload):
        """Create a test KPI result"""
        return AnalyticsResult.objects.create(
            company=company_with_admin,
            upload=data_upload,
            result_type='kpi',
            title='Total Revenue',
            value={'amount': 100000, 'currency': 'CLP'},
            visible_to_roles=[]  # Visible to all
        )

    @pytest.fixture
    def admin_only_result(self, db, company_with_admin, data_upload):
        """Create a result visible only to admins"""
        return AnalyticsResult.objects.create(
            company=company_with_admin,
            upload=data_upload,
            result_type='alert',
            title='Critical Alert',
            value={'message': 'Low stock alert'},
            visible_to_roles=['admin']
        )

    def test_list_results_success(self, authenticated_client, kpi_result):
        """Test authenticated user can list analytics results"""
        response = authenticated_client.get('/api/analytics/results/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1

    def test_list_results_role_filtering_admin(
        self, authenticated_client, kpi_result, admin_only_result
    ):
        """Test admin sees all results including admin-only"""
        response = authenticated_client.get('/api/analytics/results/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        result_ids = [r['id'] for r in results]
        assert str(kpi_result.id) in result_ids
        assert str(admin_only_result.id) in result_ids

    def test_list_results_role_filtering_analyst(
        self, api_client, create_user, company_with_analyst, kpi_result, admin_only_result, db
    ):
        """Test analyst doesn't see admin-only results"""
        # Update admin_only_result to belong to same company
        admin_only_result.company = company_with_analyst
        admin_only_result.save()
        kpi_result.company = company_with_analyst
        kpi_result.save()

        # Authenticate as analyst
        analyst_user = create_user(email='analyst@example.com')
        api_client.force_authenticate(user=analyst_user)
        from apps.accounts.models import CompanyMember
        CompanyMember.objects.create(
            company=company_with_analyst,
            user=analyst_user,
            role='analyst'
        )

        response = api_client.get('/api/analytics/results/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        result_ids = [r['id'] for r in results]
        assert str(kpi_result.id) in result_ids
        assert str(admin_only_result.id) not in result_ids

    def test_get_results_by_type(self, authenticated_client, kpi_result):
        """Test filtering results by type"""
        response = authenticated_client.get(
            '/api/analytics/results/by_type/?result_type=kpi'
        )

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert all(r['result_type'] == 'kpi' for r in results)

    def test_get_results_by_type_missing_param(self, authenticated_client):
        """Test by_type endpoint requires result_type parameter"""
        response = authenticated_client.get('/api/analytics/results/by_type/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
