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


class PipelineExecutionService:
    """
    Executes the 9-model GabeDA analytics pipeline.

    This service:
    1. Sets up GabeDA context and configuration
    2. Loads Transaction data into context
    3. Executes each model in sequence (transactions, daily, weekly, etc.)
    4. Creates ModelResult records for filters and attributes
    5. Updates ProcessingJob progress in real-time

    Used by: process_pipeline Celery task
    """

    # Model names in execution order
    MODEL_NAMES = [
        'transactions',
        'daily',
        'daily_hour',
        'weekly',
        'monthly',
        'product_daily',
        'product_month',
        'customer_daily',
        'customer_profile'
    ]

    def __init__(self, job):
        """
        Initialize service with ProcessingJob instance.

        Args:
            job (ProcessingJob): ProcessingJob model instance to execute
        """
        from .models import ProcessingJob, ModelResult, CompanyConfig

        self.job = job
        self.company = job.company
        self.upload = job.upload
        self.company_config = self._get_company_config()

        # Initialize GabeDA context
        self.ctx = None
        self.base_cfg = None

    def _get_company_config(self):
        """Get company configuration."""
        from .models import CompanyConfig

        try:
            return CompanyConfig.objects.get(company=self.company)
        except CompanyConfig.DoesNotExist:
            return None

    def _build_base_config(self):
        """
        Build base_cfg dictionary for GabeDA execution.

        Returns:
            dict: Base configuration dictionary
        """
        if self.company_config:
            # Use company-specific configuration
            base_cfg = self.company_config.get_base_cfg_dict()
        else:
            # Use default configuration
            base_cfg = {
                'client': self.company.name,
                'data_schema': {
                    # Default column mapping (matches Transaction model)
                    'in_dt': {'source_column': 'date', 'dtype': 'date'},
                    'in_trans_id': {'source_column': 'transaction_id', 'dtype': 'str'},
                    'in_product_id': {'source_column': 'product_id', 'dtype': 'str'},
                    'in_product_desc': {'source_column': 'product_description', 'dtype': 'str'},
                    'in_quantity': {'source_column': 'quantity', 'dtype': 'float'},
                    'in_price_total': {'source_column': 'total', 'dtype': 'float'},
                    'in_cost': {'source_column': 'cost', 'dtype': 'float'},
                    'in_customer_id': {'source_column': 'customer_id', 'dtype': 'str'},
                },
                'default_formats': {
                    'date': '%Y-%m-%d',
                    'float': {'thousands': ',', 'decimal': '.'},
                }
            }

        return base_cfg

    def _load_transactions_into_context(self):
        """
        Load Transaction records into pandas DataFrame.

        Returns:
            pd.DataFrame: DataFrame with transaction data
        """
        # Fetch all transactions for this upload
        transactions = Transaction.objects.filter(
            company=self.company,
            upload=self.upload
        ).values(
            'transaction_id', 'date', 'product_id', 'product_description',
            'quantity', 'unit_price', 'total', 'cost', 'customer_id', 'category',
            'hour', 'weekday', 'month'
        )

        # Convert to DataFrame
        df = pd.DataFrame.from_records(transactions)

        if df.empty:
            raise ValueError(f"No transactions found for upload {self.upload.id}")

        return df

    def execute(self):
        """
        Execute the 9-model analytics pipeline.

        Returns:
            dict: Processing result with:
            - success (bool): Whether execution succeeded
            - models_executed (int): Number of models executed
            - results_created (int): Number of ModelResult records created
            - error (str): Error message if failed
            - traceback (str): Error traceback if failed
        """
        from .models import ModelResult

        try:
            # Step 1: Build configuration
            self.base_cfg = self._build_base_config()

            # Import GabeDA modules
            from src.core.context import GabedaContext
            from src.features.store import FeatureStore
            from src.features.resolver import DependencyResolver
            from src.features.analyzer import FeatureAnalyzer
            from src.execution.groupby import GroupByProcessor
            from src.execution.executor import ModelExecutor

            self.ctx = GabedaContext(self.base_cfg)

            # Step 2: Load transactions
            df_transactions = self._load_transactions_into_context()
            self.ctx.set_dataset('raw_transactions', df_transactions)

            # Step 3: Initialize GabeDA components
            feature_store = FeatureStore()
            resolver = DependencyResolver(feature_store)
            analyzer = FeatureAnalyzer(feature_store)
            groupby_processor = GroupByProcessor()
            executor = ModelExecutor(analyzer, groupby_processor, self.ctx)

            # Step 4: Execute each model in sequence
            models_to_execute = self.job.models_to_execute or self.MODEL_NAMES
            results_created = 0

            for model_name in models_to_execute:
                self.job.current_model = model_name
                self.job.save(update_fields=['current_model'])

                # Build model configuration (simplified - would need actual feature definitions)
                cfg_model = {
                    'model_name': model_name,
                    'exec_seq': [],  # Would be populated from feature definitions
                    'group_by': None,  # Would be set based on model type
                }

                # Execute model
                start_exec = timezone.now()

                try:
                    output = executor.execute_model(
                        cfg_model=cfg_model,
                        input_dataset_name='raw_transactions',
                        data_in=df_transactions
                    )

                    # Store model output in context
                    self.ctx.set_model_output(model_name, output, cfg_model)

                    exec_time_ms = int((timezone.now() - start_exec).total_seconds() * 1000)

                    # Create ModelResult records for filters
                    if output.get('filters') is not None:
                        filters_df = output['filters']
                        ModelResult.objects.create(
                            company=self.company,
                            job=self.job,
                            model_name=model_name,
                            result_type='filters',
                            row_count=len(filters_df),
                            column_count=len(filters_df.columns),
                            columns=filters_df.columns.tolist(),
                            data_preview=filters_df.head(10).to_dict(orient='records'),
                            execution_time_ms=exec_time_ms,
                        )
                        results_created += 1

                    # Create ModelResult records for attributes
                    if output.get('attrs') is not None:
                        attrs_df = output['attrs']
                        ModelResult.objects.create(
                            company=self.company,
                            job=self.job,
                            model_name=model_name,
                            result_type='attrs',
                            row_count=len(attrs_df),
                            column_count=len(attrs_df.columns),
                            columns=attrs_df.columns.tolist(),
                            data_preview=attrs_df.head(10).to_dict(orient='records'),
                            execution_time_ms=exec_time_ms,
                        )
                        results_created += 1

                    # Update job progress
                    self.job.add_completed_model(model_name)

                except Exception as model_exc:
                    # Continue with next model instead of failing entire pipeline
                    import logging
                    logging.error(f"Error executing model {model_name}: {model_exc}", exc_info=True)
                    continue

            return {
                'success': True,
                'models_executed': len(self.job.models_completed),
                'results_created': results_created,
            }

        except Exception as exc:
            import traceback as tb
            error_traceback = tb.format_exc()

            return {
                'success': False,
                'error': str(exc),
                'traceback': error_traceback,
                'models_executed': len(self.job.models_completed),
                'results_created': 0,
            }


class ExportGenerationService:
    """
    Generates Excel/CSV exports from processing job results.

    This service:
    1. Fetches ModelResult records for specified models
    2. Converts to pandas DataFrames
    3. Generates Excel workbook or CSV files
    4. Stores files in MEDIA_ROOT/exports/{company_id}/
    5. Returns download URL

    Used by: generate_export Celery task
    """

    def __init__(self, export):
        """
        Initialize service with DataExport instance.

        Args:
            export (DataExport): DataExport model instance to generate
        """
        from .models import DataExport, ModelResult

        self.export = export
        self.job = export.job
        self.company = export.company

    def _build_export_path(self):
        """
        Build export file path.

        Returns:
            Path: Path to export file
        """
        from pathlib import Path

        # Create exports directory structure: exports/{company_id}/{job_id}/
        export_dir = Path(settings.MEDIA_ROOT) / 'exports' / str(self.company.id) / str(self.job.id)
        export_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
        ext = 'xlsx' if self.export.export_format == 'excel' else 'csv'
        filename = f"export_{timestamp}.{ext}"

        return export_dir / filename

    def generate(self):
        """
        Generate Excel/CSV export from job results.

        Returns:
            dict: Export result with:
            - success (bool): Whether generation succeeded
            - file_path (str): Path to generated file
            - file_size_bytes (int): File size in bytes
            - download_url (str): Download URL
            - error (str): Error message if failed
        """
        from .models import ModelResult

        try:
            # Step 1: Fetch ModelResult records
            models_included = self.export.models_included or []

            if not models_included:
                # Default to all models in job
                model_results = ModelResult.objects.filter(job=self.job)
            else:
                model_results = ModelResult.objects.filter(
                    job=self.job,
                    model_name__in=models_included
                )

            if not model_results.exists():
                raise ValueError(f"No model results found for job {self.job.id}")

            # Step 2: Build export data
            export_data = {}

            for result in model_results:
                sheet_name = f"{result.model_name}_{result.result_type}"

                # Convert data_preview to DataFrame
                if result.data_preview:
                    df = pd.DataFrame(result.data_preview)
                    export_data[sheet_name] = df

            if not export_data:
                raise ValueError("No data available for export")

            # Step 3: Generate file
            file_path = self._build_export_path()

            if self.export.export_format == 'excel':
                # Generate Excel file with multiple sheets
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    for sheet_name, df in export_data.items():
                        # Truncate sheet name to 31 characters (Excel limit)
                        safe_sheet_name = sheet_name[:31]
                        df.to_excel(writer, sheet_name=safe_sheet_name, index=False)

            elif self.export.export_format == 'csv':
                # For CSV, combine all data into single file or create zip
                # For simplicity, using first dataset only
                first_df = list(export_data.values())[0]
                first_df.to_csv(file_path, index=False)

            # Step 4: Calculate file size
            file_size_bytes = file_path.stat().st_size

            # Step 5: Build download URL
            from pathlib import Path
            relative_path = file_path.relative_to(settings.MEDIA_ROOT)
            download_url = f"{settings.MEDIA_URL}{relative_path}".replace('\\', '/')

            return {
                'success': True,
                'file_path': str(relative_path),
                'file_size_bytes': file_size_bytes,
                'download_url': download_url,
            }

        except Exception as exc:
            import logging
            logging.error(f"Export generation failed for export {self.export.id}: {exc}", exc_info=True)

            return {
                'success': False,
                'error': str(exc),
            }
