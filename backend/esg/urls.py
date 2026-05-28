from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityRecordViewSet,
    DashboardSummaryView,
    DataSourceViewSet,
    IngestionJobViewSet,
    TenantViewSet,
)

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'datasources', DataSourceViewSet, basename='datasource')
router.register(r'ingestions', IngestionJobViewSet, basename='ingestion')
router.register(r'activities', ActivityRecordViewSet, basename='activity')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/summary/', DashboardSummaryView.as_view(), name='dashboard-summary'),
]
