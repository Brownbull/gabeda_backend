from django.contrib import admin
from .models import DataUpload, Transaction, Dataset, AnalyticsResult


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
