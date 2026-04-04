from django.urls import path

from . import views

app_name = 'machine_learning'

urlpatterns = [
    path('face/docs/', views.face_privacy_docs, name='face_docs'),
    path('face/enroll/', views.enroll_face, name='enroll_face'),
    path('face/verify-card/', views.verify_face_for_card, name='verify_face_for_card'),
    path('face/scan-lookup/', views.admin_doctor_face_scan, name='face_scan_lookup'),
    path('face/live/', views.live_face_scan, name='live_face_scan'),
]
