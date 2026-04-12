from django.urls import path
from .views import (
    MedicineTemplateListView, MedicineTemplateDetailView, BulkStockUploadView, low_stock_alerts
)

app_name = "inventory"

urlpatterns = [
    path('medicines/', MedicineTemplateListView.as_view(), name='medicine_list'),
    path('medicines/<int:pk>/', MedicineTemplateDetailView.as_view(), name='medicine_detail'),
    path('bulk-upload/', BulkStockUploadView.as_view(), name='bulk_upload'),
    path('low-stock-alerts/', low_stock_alerts, name='low_stock_alerts'),
]