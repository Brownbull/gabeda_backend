"""
Analytics Services - Bridge between Django and GabeDA Analytics Engine

This module provides services to integrate Django models with the GabeDA
analytics pipeline located at /src in the main project.
"""
import os
import sys
import pandas as pd
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from .models import DataUpload, Transaction, Dataset, AnalyticsResult


class DatasetGenerationService:
    """
    Service to generate datasets and analytics using GabeDA pipeline

    Bridges Django backend with GabeDA /src analytics engine:
    1. Load CSV file into pandas DataFrame
    2. Map columns using company.column_config
    3. Execute GabeDA pipeline
    4. Save generated datasets
    5. Create AnalyticsResult records
    """

    def __init__(self, data_upload):
        """
        Initialize service with a DataUpload instance

        Args:
            data_upload (DataUpload): The upload to process
        """
        self.data_upload = data_upload
        self.company = data_upload.company
        self.column_config = data_upload.company.column_config or {}
        self.context_folder = None
        self.datasets_created = []
        self.results_created = []

    def process(self):
        """
        Main processing pipeline

        Returns:
            dict: Summary of processing results
        """
        try:
            # Update status to processing
            self.data_upload.status = 'processing'
            self.data_upload.processing_started_at = timezone.now()
            self.data_upload.save()

            # Step 1: Load CSV into DataFrame
            df = self._load_csv()

            # Step 2: Validate and map columns
            df = self._validate_and_map_columns(df)

            # Step 3: Save transactions to database
            self._save_transactions(df)

            # Step 4: Run GabeDA analytics pipeline
            analytics_results = self._run_gabeda_pipeline(df)

            # Step 5: Save analytics results
            self._save_analytics_results(analytics_results)

            # Update status to completed
            self.data_upload.status = 'completed'
            self.data_upload.processing_completed_at = timezone.now()
            self.data_upload.row_count = len(df)
            date_col = self.column_config.get('date_col', 'fecha')
            self.data_upload.analysis_start_date = df[date_col].min().date() if date_col in df.columns else None
            self.data_upload.analysis_end_date = df[date_col].max().date() if date_col in df.columns else None
            self.data_upload.save()

            return {
                'success': True,
                'upload_id': str(self.data_upload.id),
                'row_count': len(df),
                'transactions_created': len(df),
                'datasets_created': len(self.datasets_created),
                'results_created': len(self.results_created),
                'context_folder': self.context_folder
            }

        except Exception as e:
            # Update status to failed
            self.data_upload.status = 'failed'
            self.data_upload.error_message = str(e)
            self.data_upload.processing_completed_at = timezone.now()
            self.data_upload.save()

            return {
                'success': False,
                'upload_id': str(self.data_upload.id),
                'error': str(e)
            }

    def _load_csv(self):
        """
        Load CSV file into pandas DataFrame

        Returns:
            pd.DataFrame: Loaded data
        """
        file_path = self.data_upload.file_path

        # Normalize path separators for current OS
        file_path = os.path.normpath(file_path)

        # If path doesn't exist as-is, try prepending MEDIA_ROOT
        if not os.path.exists(file_path):
            # Remove 'media/' prefix if present (from default_storage.save)
            clean_path = file_path.replace('media/', '').replace('media\\', '')
            # Normalize again after cleaning
            clean_path = os.path.normpath(clean_path)
            file_path = os.path.join(settings.MEDIA_ROOT, clean_path)

        # Final check - if still doesn't exist, raise clear error
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"CSV file not found at: {file_path}\n"
                f"Original path: {self.data_upload.file_path}\n"
                f"MEDIA_ROOT: {settings.MEDIA_ROOT}"
            )

        # Load CSV with pandas
        df = pd.read_csv(file_path)

        return df

    def _validate_and_map_columns(self, df):
        """
        Validate required columns and map to standard names

        Args:
            df (pd.DataFrame): Input dataframe

        Returns:
            pd.DataFrame: Validated and mapped dataframe
        """
        # Get column mapping from company config
        date_col = self.column_config.get('date_col', 'fecha')
        product_col = self.column_config.get('product_col', 'producto')
        description_col = self.column_config.get('description_col', 'glosa')
        revenue_col = self.column_config.get('revenue_col', 'total')
        quantity_col = self.column_config.get('quantity_col', 'cantidad')
        transaction_col = self.column_config.get('transaction_col', 'trans_id')

        # Validate required columns exist
        required_cols = [date_col, product_col, description_col, revenue_col, quantity_col, transaction_col]
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Parse date column
        df[date_col] = pd.to_datetime(df[date_col])

        # Extract time components if not already present
        if 'hour' not in df.columns and 'hora' in df.columns:
            df['hour'] = df['hora']
        elif 'hour' not in df.columns:
            df['hour'] = df[date_col].dt.hour

        if 'weekday' not in df.columns:
            df['weekday'] = df[date_col].dt.weekday

        if 'month' not in df.columns:
            df['month'] = df[date_col].dt.month

        return df

    def _save_transactions(self, df):
        """
        Save transactions to database

        Args:
            df (pd.DataFrame): Transaction data
        """
        # Get column names
        date_col = self.column_config.get('date_col', 'fecha')
        product_col = self.column_config.get('product_col', 'producto')
        description_col = self.column_config.get('description_col', 'glosa')
        revenue_col = self.column_config.get('revenue_col', 'total')
        quantity_col = self.column_config.get('quantity_col', 'cantidad')
        transaction_col = self.column_config.get('transaction_col', 'trans_id')
        cost_col = self.column_config.get('cost_col', 'costo')

        # Prepare transaction records
        transactions = []
        for _, row in df.iterrows():
            # Calculate unit price
            quantity = float(row[quantity_col])
            total = float(row[revenue_col])
            unit_price = total / quantity if quantity > 0 else 0

            transaction = Transaction(
                company=self.company,
                upload=self.data_upload,
                transaction_id=str(row[transaction_col]),
                date=row[date_col].date(),
                product_id=str(row[product_col]),
                product_description=str(row[description_col]),
                quantity=quantity,
                unit_price=unit_price,
                total=total,
                cost=float(row[cost_col]) if cost_col and cost_col in df.columns else None,
                customer_id=str(row.get('customer_id', '')),
                category=str(row.get('category', '')),
                hour=int(row.get('hour', 0)) if pd.notna(row.get('hour')) else None,
                weekday=int(row.get('weekday', 0)) if pd.notna(row.get('weekday')) else None,
                month=int(row.get('month', 0)) if pd.notna(row.get('month')) else None,
            )
            transactions.append(transaction)

        # Bulk create for performance
        Transaction.objects.bulk_create(transactions, batch_size=1000, ignore_conflicts=True)

    def _run_gabeda_pipeline(self, df):
        """
        Run GabeDA analytics pipeline

        Args:
            df (pd.DataFrame): Transaction data

        Returns:
            dict: Analytics results
        """
        try:
            # Import GabeDA modules
            from src.core.context import GabedaContext
            from src.preprocessing.loaders import DataLoader
            from src.preprocessing.schema import SchemaProcessor
            from src.features.store import FeatureStore
            from src.features.resolver import DependencyResolver
            from src.execution.executor import ModelExecutor

            # Create context with company_id
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            context_name = f"{self.company.name}_{timestamp}"

            context = GabedaContext(
                project_name=context_name,
                company_id=str(self.company.id)  # Add company_id for multi-tenancy
            )

            self.context_folder = context.context_folder

            # Load data from DataFrame
            data_loader = DataLoader(context)

            # Check if DataLoader has load_from_dataframe method
            if hasattr(data_loader, 'load_from_dataframe'):
                data_loader.load_from_dataframe(df, dataset_name='transactions')
            else:
                # Fallback: Save to temp CSV and load
                temp_csv_path = os.path.join(context.context_folder, 'temp_transactions.csv')
                df.to_csv(temp_csv_path, index=False)
                data_loader.load_csv(temp_csv_path, dataset_name='transactions')

            # Process schema
            schema_processor = SchemaProcessor(context)
            schema_processor.process_all()

            # Create feature store and resolve dependencies
            feature_store = FeatureStore(context)
            resolver = DependencyResolver(feature_store)
            execution_order = resolver.resolve()

            # Execute pipeline
            executor = ModelExecutor(context, feature_store)
            executor.execute_all(execution_order)

            # Extract results
            results = {
                'kpis': self._extract_kpis(context),
                'alerts': self._extract_alerts(context),
                'pareto': self._extract_pareto(context),
                'inventory': self._extract_inventory(context),
                'peak_times': self._extract_peak_times(context),
            }

            # Save datasets metadata
            self._save_dataset_metadata(context)

            return results

        except ImportError as e:
            # GabeDA modules not available - return mock results for testing
            return self._generate_mock_results(df)

    def _extract_kpis(self, context):
        """Extract KPI results from context"""
        # TODO: Implement KPI extraction from GabeDA context
        return {}

    def _extract_alerts(self, context):
        """Extract alert results from context"""
        # TODO: Implement alert extraction
        return []

    def _extract_pareto(self, context):
        """Extract Pareto analysis results"""
        # TODO: Implement Pareto extraction
        return {}

    def _extract_inventory(self, context):
        """Extract inventory health results"""
        # TODO: Implement inventory extraction
        return {}

    def _extract_peak_times(self, context):
        """Extract peak times analysis"""
        # TODO: Implement peak times extraction
        return {}

    def _save_dataset_metadata(self, context):
        """Save dataset metadata to database"""
        # TODO: Scan context folder and create Dataset records
        pass

    def _generate_mock_results(self, df):
        """
        Generate mock analytics results for testing (when GabeDA not available)

        Args:
            df (pd.DataFrame): Transaction data

        Returns:
            dict: Mock analytics results
        """
        revenue_col = self.column_config.get('revenue_col', 'total')
        quantity_col = self.column_config.get('quantity_col', 'cantidad')
        product_col = self.column_config.get('product_col', 'producto')

        total_revenue = df[revenue_col].sum()
        total_transactions = len(df)
        avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
        total_quantity = df[quantity_col].sum()

        # Top products
        top_products = df.groupby(product_col)[revenue_col].sum().nlargest(5).to_dict()

        return {
            'kpis': {
                'total_revenue': float(total_revenue),
                'total_transactions': int(total_transactions),
                'avg_transaction': float(avg_transaction),
                'total_quantity': float(total_quantity),
            },
            'alerts': [],
            'pareto': {
                'top_products': {str(k): float(v) for k, v in top_products.items()}
            },
            'inventory': {},
            'peak_times': {},
        }

    def _save_analytics_results(self, analytics_results):
        """
        Save analytics results to database

        Args:
            analytics_results (dict): Results from pipeline
        """
        # Save KPIs
        if analytics_results.get('kpis'):
            result = AnalyticsResult.objects.create(
                company=self.company,
                upload=self.data_upload,
                result_type='kpi',
                title='Key Performance Indicators',
                value=analytics_results['kpis'],
                visible_to_roles=[]  # Visible to all
            )
            self.results_created.append(result)

        # Save Pareto analysis
        if analytics_results.get('pareto'):
            result = AnalyticsResult.objects.create(
                company=self.company,
                upload=self.data_upload,
                result_type='pareto',
                title='Pareto Analysis - Top Products',
                value=analytics_results['pareto'],
                visible_to_roles=[]
            )
            self.results_created.append(result)

        # Save alerts
        if analytics_results.get('alerts'):
            result = AnalyticsResult.objects.create(
                company=self.company,
                upload=self.data_upload,
                result_type='alert',
                title='Business Alerts',
                value={'alerts': analytics_results['alerts']},
                visible_to_roles=['admin', 'business_owner']  # Admin and business owner only
            )
            self.results_created.append(result)

        # Save inventory health
        if analytics_results.get('inventory'):
            result = AnalyticsResult.objects.create(
                company=self.company,
                upload=self.data_upload,
                result_type='inventory',
                title='Inventory Health',
                value=analytics_results['inventory'],
                visible_to_roles=['admin', 'business_owner', 'operations_manager']
            )
            self.results_created.append(result)

        # Save peak times
        if analytics_results.get('peak_times'):
            result = AnalyticsResult.objects.create(
                company=self.company,
                upload=self.data_upload,
                result_type='peak_times',
                title='Peak Times Analysis',
                value=analytics_results['peak_times'],
                visible_to_roles=['admin', 'operations_manager']
            )
            self.results_created.append(result)
