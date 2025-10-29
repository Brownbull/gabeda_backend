from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CSVUploadView,
    DataUploadViewSet,
    TransactionViewSet,
    DatasetViewSet,
    AnalyticsResultViewSet
)

router = DefaultRouter()
router.register(r'uploads', DataUploadViewSet, basename='upload')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'datasets', DatasetViewSet, basename='dataset')
router.register(r'results', AnalyticsResultViewSet, basename='analytics-result')

urlpatterns = [
    # CSV Upload endpoint
    path('companies/<uuid:company_id>/upload/', CSVUploadView.as_view(), name='csv-upload'),

    # Router URLs (uploads, transactions, datasets, results)
    path('', include(router.urls)),
]
