from django.urls import path

from .views import (
    DoctorApprovalDashboardView,
    DoctorDetailView,
    DoctorFollowToggleView,
    DoctorHubView,
    DeletePatientLogView,
    DoctorPatientDetailView,
    DoctorPatientsView,
    DoctorRateView,
    DoctorRegistrationView,
    DoctorReportView,
    EditPatientLogView,
    PatientAnalysisView,
    PatientEntryDetailView,
    ReviewDoctorRequestView,
    CreatePatientLogView,
    SendPatientLogView,
    PatientLogDetailView,
    MyPatientLogsView,
    PatientLogFillView,
)

app_name = 'doctor'

urlpatterns = [
    path('', DoctorHubView.as_view(), name='hub'),
    path('<int:doctor_id>/', DoctorDetailView.as_view(), name='detail'),
    path('<int:doctor_id>/follow/', DoctorFollowToggleView.as_view(), name='follow_toggle'),
    path('<int:doctor_id>/rate/', DoctorRateView.as_view(), name='rate'),
    path('<int:doctor_id>/report/', DoctorReportView.as_view(), name='report'),
    path('register/', DoctorRegistrationView.as_view(), name='register'),
    path('approval/', DoctorApprovalDashboardView.as_view(), name='approval_dashboard'),
    path('approval/<int:request_id>/', ReviewDoctorRequestView.as_view(), name='review_request'),
    # Patient Log — doctor side
    path('patients/', DoctorPatientsView.as_view(), name='patients'),
    path('patients/<int:patient_id>/', DoctorPatientDetailView.as_view(), name='patient_detail'),
    path('patients/<int:patient_id>/analysis/', PatientAnalysisView.as_view(), name='patient_analysis'),
    path('patients/<int:patient_id>/create-log/', CreatePatientLogView.as_view(), name='create_patient_log'),
    path('log/<int:log_id>/', PatientLogDetailView.as_view(), name='patient_log_detail'),
    path('log/<int:log_id>/edit/', EditPatientLogView.as_view(), name='edit_patient_log'),
    path('log/<int:log_id>/delete/', DeletePatientLogView.as_view(), name='delete_patient_log'),
    path('log/<int:log_id>/send/', SendPatientLogView.as_view(), name='send_patient_log'),
    path('entry/<int:entry_id>/', PatientEntryDetailView.as_view(), name='patient_entry_detail'),
    # Patient Log — patient side
    path('my-logs/', MyPatientLogsView.as_view(), name='my_patient_logs'),
    path('my-logs/<int:log_id>/fill/', PatientLogFillView.as_view(), name='patient_log_fill'),
]
