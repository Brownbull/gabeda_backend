"""
Test suite for DatasetGenerationService
"""
import pytest
import pandas as pd
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.analytics.models import DataUpload, Transaction, AnalyticsResult
from apps.analytics.services import DatasetGenerationService

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def sample_csv_data():
    """Create sample CSV data"""
    return b"""trans_id,fecha,producto,glosa,cantidad,total,costo
T001,2025-01-15,P001,Product One,10,1000,800
T002,2025-01-15,P002,Product Two,5,500,400
T003,2025-01-16,P001,Product One,15,1500,1200
T004,2025-01-16,P003,Product Three,8,800,640
T005,2025-01-17,P002,Product Two,12,1200,960
"""


@pytest.fixture
def csv_file(sample_csv_data):
    """Create CSV file for upload"""
    return SimpleUploadedFile("test_transactions.csv", sample_csv_data, content_type="text/csv")


@pytest.fixture
def data_upload_with_file(db, company_with_admin, user, csv_file, tmp_path):
    """Create a DataUpload with an actual CSV file"""
    import os
    from django.conf import settings

    # Create media directory if it doesn't exist
    media_dir = tmp_path / "media" / "uploads" / str(company_with_admin.id)
    media_dir.mkdir(parents=True, exist_ok=True)

    # Save file
    file_path = media_dir / "test_transactions.csv"
    with open(file_path, 'wb') as f:
        f.write(csv_file.read())

    # Create DataUpload
    upload = DataUpload.objects.create(
        company=company_with_admin,
        uploaded_by=user,
        file_name="test_transactions.csv",
        file_size=csv_file.size,
        file_path=str(file_path),
        status='pending'
    )

    return upload


class TestDatasetGenerationService:
    """Test DatasetGenerationService"""

    def test_service_initialization(self, data_upload_with_file):
        """Test service can be initialized"""
        service = DatasetGenerationService(data_upload_with_file)

        assert service.data_upload == data_upload_with_file
        assert service.company == data_upload_with_file.company
        assert service.column_config is not None

    def test_load_csv(self, data_upload_with_file):
        """Test CSV loading"""
        service = DatasetGenerationService(data_upload_with_file)
        df = service._load_csv()

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert 'trans_id' in df.columns
        assert 'fecha' in df.columns
        assert 'producto' in df.columns

    def test_validate_and_map_columns(self, data_upload_with_file):
        """Test column validation and mapping"""
        service = DatasetGenerationService(data_upload_with_file)
        df = service._load_csv()
        df = service._validate_and_map_columns(df)

        # Check date was parsed
        assert pd.api.types.is_datetime64_any_dtype(df['fecha'])

        # Check time components were added
        assert 'weekday' in df.columns
        assert 'month' in df.columns

    def test_save_transactions(self, data_upload_with_file):
        """Test transactions are saved to database"""
        service = DatasetGenerationService(data_upload_with_file)
        df = service._load_csv()
        df = service._validate_and_map_columns(df)

        # Should have no transactions initially
        assert Transaction.objects.filter(upload=data_upload_with_file).count() == 0

        # Save transactions
        service._save_transactions(df)

        # Should have 5 transactions now
        transactions = Transaction.objects.filter(upload=data_upload_with_file)
        assert transactions.count() == 5

        # Verify transaction data (order by transaction_id)
        first_transaction = transactions.order_by('transaction_id').first()
        assert first_transaction.transaction_id == 'T001'
        assert first_transaction.product_id == 'P001'
        assert first_transaction.product_description == 'Product One'
        assert first_transaction.quantity == 10
        assert first_transaction.total == 1000
        assert first_transaction.cost == 800

    def test_generate_mock_results(self, data_upload_with_file):
        """Test mock analytics results generation"""
        service = DatasetGenerationService(data_upload_with_file)
        df = service._load_csv()
        df = service._validate_and_map_columns(df)

        results = service._generate_mock_results(df)

        assert 'kpis' in results
        assert 'alerts' in results
        assert 'pareto' in results

        # Check KPIs
        kpis = results['kpis']
        assert kpis['total_revenue'] == 5000  # 1000+500+1500+800+1200
        assert kpis['total_transactions'] == 5
        assert kpis['avg_transaction'] == 1000  # 5000/5
        assert kpis['total_quantity'] == 50  # 10+5+15+8+12

        # Check Pareto has top products
        assert 'top_products' in results['pareto']
        top_products = results['pareto']['top_products']
        assert len(top_products) > 0

    def test_save_analytics_results(self, data_upload_with_file):
        """Test analytics results are saved to database"""
        service = DatasetGenerationService(data_upload_with_file)

        # Create mock results
        analytics_results = {
            'kpis': {
                'total_revenue': 5000,
                'total_transactions': 5,
            },
            'pareto': {
                'top_products': {'P001': 2500, 'P002': 1700}
            },
            'alerts': [],
            'inventory': {},
            'peak_times': {},
        }

        # Should have no results initially
        assert AnalyticsResult.objects.filter(upload=data_upload_with_file).count() == 0

        # Save results
        service._save_analytics_results(analytics_results)

        # Should have results now
        results = AnalyticsResult.objects.filter(upload=data_upload_with_file)
        assert results.count() >= 2  # At least KPIs and Pareto

        # Verify KPI result
        kpi_result = results.filter(result_type='kpi').first()
        assert kpi_result is not None
        assert kpi_result.title == 'Key Performance Indicators'
        assert kpi_result.value['total_revenue'] == 5000

    def test_process_full_pipeline(self, data_upload_with_file):
        """Test full processing pipeline"""
        service = DatasetGenerationService(data_upload_with_file)

        # Initially pending
        assert data_upload_with_file.status == 'pending'

        # Process
        result = service.process()

        # Check result (print error if failed for debugging)
        if not result['success']:
            print(f"Processing failed: {result.get('error')}")
        assert result['success'] is True
        assert result['row_count'] == 5
        assert result['transactions_created'] == 5
        assert result['results_created'] >= 2

        # Verify upload status updated
        data_upload_with_file.refresh_from_db()
        assert data_upload_with_file.status == 'completed'
        assert data_upload_with_file.row_count == 5
        assert data_upload_with_file.processing_completed_at is not None

        # Verify transactions created
        assert Transaction.objects.filter(upload=data_upload_with_file).count() == 5

        # Verify analytics results created
        assert AnalyticsResult.objects.filter(upload=data_upload_with_file).count() >= 2

    def test_process_handles_errors(self, data_upload_with_file):
        """Test error handling in processing"""
        # Delete the CSV file to cause an error
        import os
        if os.path.exists(data_upload_with_file.file_path):
            os.remove(data_upload_with_file.file_path)

        service = DatasetGenerationService(data_upload_with_file)
        result = service.process()

        # Should fail gracefully
        assert result['success'] is False
        assert 'error' in result

        # Upload status should be failed
        data_upload_with_file.refresh_from_db()
        assert data_upload_with_file.status == 'failed'
        assert data_upload_with_file.error_message != ''


class TestCSVUploadIntegration:
    """Test CSV upload with DatasetGenerationService"""

    def test_csv_upload_triggers_processing(
        self, authenticated_client, company_with_admin, csv_file
    ):
        """Test CSV upload endpoint triggers processing"""
        response = authenticated_client.post(
            f'/api/analytics/companies/{company_with_admin.id}/upload/',
            {'file': csv_file},
            format='multipart'
        )

        assert response.status_code == 201
        assert 'upload' in response.data
        assert 'processing_result' in response.data

        # Check processing result
        processing_result = response.data['processing_result']
        if not processing_result['success']:
            print(f"Upload processing failed: {processing_result.get('error')}")
            print(f"Response data: {response.data}")
        assert processing_result['success'] is True
        assert processing_result['row_count'] == 5

        # Verify upload was processed
        upload_id = response.data['upload']['id']
        upload = DataUpload.objects.get(id=upload_id)
        assert upload.status == 'completed'

        # Verify transactions were created
        assert Transaction.objects.filter(upload=upload).count() == 5

        # Verify analytics results were created
        assert AnalyticsResult.objects.filter(upload=upload).count() >= 2
