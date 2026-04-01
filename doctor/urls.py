from django.urls import path

from .views import DoctorApprovalDashboardView, DoctorHubView, DoctorRegistrationView, ReviewDoctorRequestView

app_name = 'doctor'

urlpatterns = [
    path('', DoctorHubView.as_view(), name='hub'),
    path('register/', DoctorRegistrationView.as_view(), name='register'),
    path('approval/', DoctorApprovalDashboardView.as_view(), name='approval_dashboard'),
    path('approval/<int:request_id>/', ReviewDoctorRequestView.as_view(), name='review_request'),
]
