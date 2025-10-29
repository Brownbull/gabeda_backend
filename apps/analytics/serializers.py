from rest_framework import serializers
from .models import DataUpload, Transaction, Dataset, AnalyticsResult


class DataUploadSerializer(serializers.ModelSerializer):
    """Serializer for DataUpload model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    uploaded_by_email = serializers.EmailField(source='uploaded_by.email', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DataUpload
        fields = [
            'id', 'company', 'company_name', 'uploaded_by', 'uploaded_by_email',
            'file_name', 'file_size', 'file_path', 'status', 'status_display',
            'row_count', 'error_message', 'uploaded_at', 'processing_started_at',
            'processing_completed_at', 'analysis_start_date', 'analysis_end_date'
        ]
        read_only_fields = [
            'id', 'uploaded_by', 'file_size', 'file_path', 'status',
            'row_count', 'error_message', 'uploaded_at', 'processing_started_at',
            'processing_completed_at'
        ]


class CSVUploadSerializer(serializers.Serializer):
    """Serializer for CSV file upload"""

    file = serializers.FileField(required=True)

    def validate_file(self, value):
        """Validate uploaded file"""
        # Check file extension
        if not value.name.endswith('.csv'):
            raise serializers.ValidationError("Only CSV files are allowed.")

        # Check file size (max 50MB)
        max_size = 50 * 1024 * 1024  # 50MB in bytes
        if value.size > max_size:
            raise serializers.ValidationError(f"File size cannot exceed 50MB. Current size: {value.size / (1024*1024):.2f}MB")

        # Check file is not empty
        if value.size == 0:
            raise serializers.ValidationError("Uploaded file is empty.")

        return value


class TransactionSerializer(serializers.ModelSerializer):
    """Serializer for Transaction model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    upload_file_name = serializers.CharField(source='upload.file_name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'company', 'company_name', 'upload', 'upload_file_name',
            'transaction_id', 'date', 'product_id', 'product_description',
            'quantity', 'unit_price', 'total', 'cost', 'customer_id',
            'category', 'hour', 'weekday', 'month', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DatasetSerializer(serializers.ModelSerializer):
    """Serializer for Dataset model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    upload_file_name = serializers.CharField(source='upload.file_name', read_only=True)
    dataset_type_display = serializers.CharField(source='get_dataset_type_display', read_only=True)

    class Meta:
        model = Dataset
        fields = [
            'id', 'company', 'company_name', 'upload', 'upload_file_name',
            'name', 'dataset_type', 'dataset_type_display', 'description',
            'file_path', 'file_size', 'row_count', 'column_count',
            'context_folder', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AnalyticsResultSerializer(serializers.ModelSerializer):
    """Serializer for AnalyticsResult model"""

    company_name = serializers.CharField(source='company.name', read_only=True)
    upload_file_name = serializers.CharField(source='upload.file_name', read_only=True)
    result_type_display = serializers.CharField(source='get_result_type_display', read_only=True)

    class Meta:
        model = AnalyticsResult
        fields = [
            'id', 'company', 'company_name', 'upload', 'upload_file_name',
            'result_type', 'result_type_display', 'title', 'value',
            'metadata', 'visible_to_roles', 'created_at', 'analysis_date'
        ]
        read_only_fields = ['id', 'created_at']

    def to_representation(self, instance):
        """Filter results based on user role"""
        representation = super().to_representation(instance)

        # Get current user's role for this company
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            from apps.accounts.models import CompanyMember

            member = CompanyMember.objects.filter(
                company=instance.company,
                user=request.user
            ).first()

            if member:
                # If visible_to_roles is empty, visible to all
                # Otherwise, check if user's role is in the list
                visible_to_roles = instance.visible_to_roles
                if visible_to_roles and member.role not in visible_to_roles:
                    # User doesn't have access to this result
                    return None

        return representation


class AnalyticsResultListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing analytics results"""

    result_type_display = serializers.CharField(source='get_result_type_display', read_only=True)

    class Meta:
        model = AnalyticsResult
        fields = [
            'id', 'result_type', 'result_type_display', 'title',
            'analysis_date', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
