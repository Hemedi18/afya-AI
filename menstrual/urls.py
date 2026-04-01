from django.urls import path
from . import views

app_name = 'menstrual'

urlpatterns = [
    path('dashboard/', views.MenstrualDashboardView.as_view(), name='dashboard'),
    path('settings/', views.MenstrualSettingsView.as_view(), name='settings'),
    path('tips/new/', views.DailyTipCreateView.as_view(), name='add_tip'),
    path('reports/', views.MenstrualReportView.as_view(), name='reports'),
    path('cycle/new/', views.MenstrualCycleCreateView.as_view(), name='start_cycle'),
    path('log/new/', views.DailyLogCreateView.as_view(), name='add_log'),
    path('log/<int:pk>/edit/', views.DailyLogUpdateView.as_view(), name='edit_log'),
    path('community/', views.ForumListView.as_view(), name='community'),
    path('doctors/', views.DoctorListView.as_view(), name='doctor_list'),
    path('doctors/verify/', views.VerifyDoctorView.as_view(), name='verify_doctor'),
    path('reminder/<int:pk>/read/', views.MarkReminderReadView.as_view(), name='mark_reminder_read'),
]