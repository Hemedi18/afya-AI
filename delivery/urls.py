from django.urls import path
from .views import DeliveryDashboardView, DeliveryDetailView

app_name = "delivery"

urlpatterns = [
    path('', DeliveryDashboardView.as_view(), name='dashboard'),
    path('<int:pk>/', DeliveryDetailView.as_view(), name='detail'),
]