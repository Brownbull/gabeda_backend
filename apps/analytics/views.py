from rest_framework import viewsets, status, generics, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from apps.accounts.models import CompanyMember
from .models import DataUpload, Transaction, Dataset, AnalyticsResult
from .serializers import (
    DataUploadSerializer,
    CSVUploadSerializer,
    TransactionSerializer,
    DatasetSerializer,
    AnalyticsResultSerializer,
    AnalyticsResultListSerializer
)
import os


class CSVUploadView(generics.CreateAPIView):
    """
    API endpoint for uploading CSV files
    POST /api/analytics/companies/{company_id}/upload/
    """

    permission_classes = [IsAuthenticated]
    serializer_class = CSVUploadSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]

    def create(self, request, *args, **kwargs):
        company_id = self.kwargs.get('company_id')

        # Check if user is a member of this company
        member = CompanyMember.objects.filter(
            company_id=company_id,
            user=request.user
        ).first()

        if not member:
            return Response(
                {'error': 'You are not a member of this company.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate file
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data['file']

        # Create upload directory if it doesn't exist
        upload_dir = f'uploads/{company_id}/'
        os.makedirs(os.path.join('media', upload_dir), exist_ok=True)

        # Generate unique file name
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"{timestamp}_{uploaded_file.name}"
        file_path = os.path.join(upload_dir, file_name)

        # Save file
        full_path = default_storage.save(
            os.path.join('media', file_path),
            ContentFile(uploaded_file.read())
        )

        # Create DataUpload record
        data_upload = DataUpload.objects.create(
            company_id=company_id,
            uploaded_by=request.user,
            file_name=uploaded_file.name,
            file_size=uploaded_file.size,
            file_path=full_path,
            status='pending'
        )

        # TODO: Trigger Celery task for processing
        # from .tasks import process_csv_upload
        # process_csv_upload.delay(data_upload.id)

        return Response(
            {
                'message': 'File uploaded successfully. Processing will begin shortly.',
                'upload': DataUploadSerializer(data_upload).data
            },
            status=status.HTTP_201_CREATED
        )


class DataUploadViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing data uploads
    GET /api/analytics/uploads/ - List all uploads for user's companies
    GET /api/analytics/uploads/{id}/ - Get upload details
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DataUploadSerializer

    def get_queryset(self):
        """Return uploads for companies where user is a member"""
        user = self.request.user
        company_ids = CompanyMember.objects.filter(
            user=user
        ).values_list('company_id', flat=True)

        return DataUpload.objects.filter(
            company_id__in=company_ids
        ).select_related('company', 'uploaded_by').order_by('-uploaded_at')

    @action(detail=False, methods=['get'])
    def by_company(self, request):
        """Get uploads filtered by company"""
        company_id = request.query_params.get('company_id')

        if not company_id:
            return Response(
                {'error': 'company_id parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if user is a member
        member = CompanyMember.objects.filter(
            company_id=company_id,
            user=request.user
        ).first()

        if not member:
            return Response(
                {'error': 'You are not a member of this company.'},
                status=status.HTTP_403_FORBIDDEN
            )

        uploads = DataUpload.objects.filter(
            company_id=company_id
        ).select_related('company', 'uploaded_by').order_by('-uploaded_at')

        serializer = self.get_serializer(uploads, many=True)
        return Response(serializer.data)


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing transactions
    GET /api/analytics/transactions/ - List transactions
    GET /api/analytics/transactions/{id}/ - Get transaction details
    """

    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        """Return transactions for companies where user is a member"""
        user = self.request.user
        company_ids = CompanyMember.objects.filter(
            user=user
        ).values_list('company_id', flat=True)

        queryset = Transaction.objects.filter(
            company_id__in=company_ids
        ).select_related('company', 'upload')

        # Filter by company if specified
        company_id = self.request.query_params.get('company_id')
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        # Filter by upload if specified
        upload_id = self.request.query_params.get('upload_id')
        if upload_id:
            queryset = queryset.filter(upload_id=upload_id)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)

        return queryset.order_by('-date', 'transaction_id')


class DatasetViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing generated datasets
    GET /api/analytics/datasets/ - List datasets
    GET /api/analytics/datasets/{id}/ - Get dataset details
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DatasetSerializer

    def get_queryset(self):
        """Return datasets for companies where user is a member"""
        user = self.request.user
        company_ids = CompanyMember.objects.filter(
            user=user
        ).values_list('company_id', flat=True)

        queryset = Dataset.objects.filter(
            company_id__in=company_ids
        ).select_related('company', 'upload')

        # Filter by company if specified
        company_id = self.request.query_params.get('company_id')
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        # Filter by upload if specified
        upload_id = self.request.query_params.get('upload_id')
        if upload_id:
            queryset = queryset.filter(upload_id=upload_id)

        # Filter by dataset type
        dataset_type = self.request.query_params.get('dataset_type')
        if dataset_type:
            queryset = queryset.filter(dataset_type=dataset_type)

        return queryset.order_by('-created_at')


class AnalyticsResultViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing analytics results
    GET /api/analytics/results/ - List all results (role-filtered)
    GET /api/analytics/results/{id}/ - Get result details
    GET /api/analytics/results/by_type/?result_type=kpi - Filter by type
    """

    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return AnalyticsResultListSerializer
        return AnalyticsResultSerializer

    def get_queryset(self):
        """Return analytics results for companies where user is a member"""
        user = self.request.user
        company_ids = CompanyMember.objects.filter(
            user=user
        ).values_list('company_id', flat=True)

        queryset = AnalyticsResult.objects.filter(
            company_id__in=company_ids
        ).select_related('company', 'upload')

        # Filter by company if specified
        company_id = self.request.query_params.get('company_id')
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        # Filter by upload if specified
        upload_id = self.request.query_params.get('upload_id')
        if upload_id:
            queryset = queryset.filter(upload_id=upload_id)

        # Filter by result type
        result_type = self.request.query_params.get('result_type')
        if result_type:
            queryset = queryset.filter(result_type=result_type)

        return queryset.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        """List analytics results with role-based filtering"""
        queryset = self.filter_queryset(self.get_queryset())

        # Get user's roles for each company
        user_roles = {}
        for member in CompanyMember.objects.filter(user=request.user):
            user_roles[str(member.company_id)] = member.role

        # Filter results based on visible_to_roles
        filtered_results = []
        for result in queryset:
            company_id = str(result.company_id)
            user_role = user_roles.get(company_id)

            # If visible_to_roles is empty, visible to all
            if not result.visible_to_roles or user_role in result.visible_to_roles:
                filtered_results.append(result)

        page = self.paginate_queryset(filtered_results)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(filtered_results, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Get analytics results grouped by type"""
        queryset = self.get_queryset()

        # Get result_type from query params
        result_type = request.query_params.get('result_type')
        if not result_type:
            return Response(
                {'error': 'result_type parameter is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        results = queryset.filter(result_type=result_type)
        serializer = AnalyticsResultSerializer(
            results,
            many=True,
            context={'request': request}
        )

        # Filter out None values (results user doesn't have access to)
        filtered_data = [item for item in serializer.data if item is not None]

        return Response(filtered_data)
