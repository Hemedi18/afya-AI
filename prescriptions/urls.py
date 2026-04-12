from django.urls import path
from . import views

app_name = 'prescriptions'

urlpatterns = [
    path('', views.prescription_list, name='prescription_list'),
    path('upload/', views.prescription_upload, name='prescription_upload'),
    path('<int:pk>/', views.prescription_detail, name='prescription_detail'),
    path('<int:pk>/verify/', views.verify_prescription, name='verify_prescription'),
]