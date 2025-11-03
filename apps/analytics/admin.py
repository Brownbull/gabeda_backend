from django.contrib import admin
from .models import (
    DataUpload, Transaction, Dataset, AnalyticsResult, CompanyConfig,
    ProcessingJob, ModelResult, DataExport
)


@admin.register(DataUpload)
class DataUploadAdmin(admin.ModelAdmin):
    """Admin interface for DataUpload model"""

    list_display = ['file_name', 'company', 'uploaded_by', 'status', 'row_count', 'uploaded_at']
    list_filter = ['status', 'uploaded_at', 'company']
    search_fields = ['file_name', 'company__name', 'uploaded_by__email']
    ordering = ['-uploaded_at']

    fieldsets = (
        ('File Information', {
            'fields': ('company', 'uploaded_by', 'file_name', 'file_size', 'file_path')
        }),
        ('Processing Status', {
            'fields': ('status', 'row_count', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'processing_started_at', 'processing_completed_at')
        }),
        ('Analysis Metadata', {
            'fields': ('analysis_start_date', 'analysis_end_date')
        }),
    )

    readonly_fields = ['uploaded_at']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Admin interface for Transaction model"""

    list_display = ['transaction_id', 'company', 'date', 'product_id', 'product_description', 'total']
    list_filter = ['company', 'date', 'upload']
    search_fields = ['transaction_id', 'product_id', 'product_description', 'company__name']
    ordering = ['-date', 'transaction_id']
    date_hierarchy = 'date'

    fieldsets = (
        ('Company & Upload', {
            'fields': ('company', 'upload')
        }),
        ('Transaction Details', {
            'fields': ('transaction_id', 'date', 'product_id', 'product_description')
        }),
        ('Financial Data', {
            'fields': ('quantity', 'unit_price', 'total', 'cost')
        }),
        ('Optional Data', {
            'fields': ('customer_id', 'category')
        }),
        ('Time Components', {
            'fields': ('hour', 'weekday', 'month')
        }),
    )

    readonly_fields = ['created_at']


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
    """Admin interface for Dataset model"""

    list_display = ['name', 'dataset_type', 'company', 'upload', 'row_count', 'created_at']
    list_filter = ['dataset_type', 'company', 'created_at']
    search_fields = ['name', 'description', 'company__name']
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'upload', 'name', 'dataset_type', 'description')
        }),
        ('File Information', {
            'fields': ('file_path', 'file_size', 'row_count', 'column_count')
        }),
        ('Metadata', {
            'fields': ('context_folder', 'created_at')
        }),
    )

    readonly_fields = ['created_at']


@admin.register(AnalyticsResult)
class AnalyticsResultAdmin(admin.ModelAdmin):
    """Admin interface for AnalyticsResult model"""

    list_display = ['title', 'result_type', 'company', 'upload', 'analysis_date', 'created_at']
    list_filter = ['result_type', 'company', 'created_at', 'analysis_date']
    search_fields = ['title', 'company__name']
    ordering = ['-created_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'upload', 'result_type', 'title')
        }),
        ('Data', {
            'fields': ('value', 'metadata')
        }),
        ('Access Control', {
            'fields': ('visible_to_roles',)
        }),
        ('Timestamps', {
            'fields': ('analysis_date', 'created_at')
        }),
    )

    readonly_fields = ['created_at']


@admin.register(CompanyConfig)
class CompanyConfigAdmin(admin.ModelAdmin):
    """Admin interface for CompanyConfig model"""

    list_display = ['company', 'created_by', 'created_at', 'updated_at']
    list_filter = ['company', 'created_at', 'updated_at']
    search_fields = ['company__name', 'created_by__email']
    ordering = ['-updated_at']

    fieldsets = (
        ('Company', {
            'fields': ('company',)
        }),
        ('Configuration', {
            'fields': ('data_schema', 'default_formats')
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at')
        }),
    )

    readonly_fields = ['created_at', 'updated_at']

    def get_readonly_fields(self, request, obj=None):
        """Make company readonly on edit"""
        if obj:  # Editing existing object
            return self.readonly_fields + ['company', 'created_by']
        return self.readonly_fields


@admin.register(ProcessingJob)
class ProcessingJobAdmin(admin.ModelAdmin):
    """Admin interface for ProcessingJob model"""

    list_display = ['id', 'company', 'upload', 'status', 'progress', 'current_model', 'created_at']
    list_filter = ['status', 'company', 'created_at']
    search_fields = ['id', 'company__name', 'celery_task_id']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Job Information', {
            'fields': ('company', 'upload', 'celery_task_id')
        }),
        ('Execution Status', {
            'fields': ('status', 'progress', 'current_model', 'last_checkpoint')
        }),
        ('Model Tracking', {
            'fields': ('models_to_execute', 'models_completed'),
            'classes': ('collapse',)
        }),
        ('Performance', {
            'fields': ('processing_time_seconds',)
        }),
        ('Error Details', {
            'fields': ('error_message', 'error_traceback'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'started_at', 'completed_at')
        }),
    )

    readonly_fields = ['created_at', 'started_at', 'completed_at', 'processing_time_seconds']

    def get_readonly_fields(self, request, obj=None):
        """Make most fields readonly on edit"""
        if obj:  # Editing existing object
            return self.readonly_fields + ['company', 'upload', 'celery_task_id']
        return self.readonly_fields


@admin.register(ModelResult)
class ModelResultAdmin(admin.ModelAdmin):
    """Admin interface for ModelResult model"""

    list_display = ['model_name', 'result_type', 'company', 'job', 'row_count', 'column_count', 'created_at']
    list_filter = ['model_name', 'result_type', 'company', 'created_at']
    search_fields = ['model_name', 'company__name', 'job__id']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('company', 'job', 'model_name', 'result_type')
        }),
        ('Data Dimensions', {
            'fields': ('row_count', 'column_count', 'columns')
        }),
        ('Data Storage', {
            'fields': ('data_path', 'data_preview'),
            'classes': ('collapse',)
        }),
        ('Performance', {
            'fields': ('execution_time_ms',)
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )

    readonly_fields = ['created_at']

    def get_readonly_fields(self, request, obj=None):
        """Make most fields readonly on edit"""
        if obj:  # Editing existing object
            return self.readonly_fields + ['company', 'job', 'model_name', 'result_type']
        return self.readonly_fields


@admin.register(DataExport)
class DataExportAdmin(admin.ModelAdmin):
    """Admin interface for DataExport model"""

    list_display = ['id', 'export_format', 'company', 'job', 'status', 'requested_by', 'created_at']
    list_filter = ['export_format', 'status', 'company', 'created_at']
    search_fields = ['id', 'company__name', 'job__id', 'requested_by__email']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Export Information', {
            'fields': ('company', 'job', 'requested_by', 'export_format')
        }),
        ('Configuration', {
            'fields': ('models_included',)
        }),
        ('File Information', {
            'fields': ('file_path', 'file_size_bytes', 'download_url')
        }),
        ('Status', {
            'fields': ('status', 'celery_task_id', 'error_message')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at', 'expires_at')
        }),
    )

    readonly_fields = ['created_at', 'completed_at', 'file_size_bytes']

    def get_readonly_fields(self, request, obj=None):
        """Make most fields readonly on edit"""
        if obj:  # Editing existing object
            return self.readonly_fields + ['company', 'job', 'requested_by', 'celery_task_id']
        return self.readonly_fields
