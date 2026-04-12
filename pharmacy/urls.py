from django.urls import path
from .views import PharmacyDashboardView, PharmacyRegisterView, PharmacyDetailView, PharmacyStaffDashboardView, SubOrderUpdateStatusView

app_name = "pharmacy"

urlpatterns = [
    path('', PharmacyDashboardView.as_view(), name='dashboard'),
    path('register/', PharmacyRegisterView.as_view(), name='register'),
    path('<int:pk>/', PharmacyDetailView.as_view(), name='detail'),
    path('staff/dashboard/', PharmacyStaffDashboardView.as_view(), name='staff_dashboard'),
    path('suborder/<int:pk>/update/', SubOrderUpdateStatusView.as_view(), name='update_suborder_status'),
]