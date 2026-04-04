from django.urls import path

from .views import MedicationDetailApiView, MedicationListCreateApiView


urlpatterns = [
    path('medications/', MedicationListCreateApiView.as_view(), name='medication_list_create'),
    path('medications/<int:medication_id>/', MedicationDetailApiView.as_view(), name='medication_detail'),
]
