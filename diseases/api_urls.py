from django.urls import path

from .views import (
    DiseaseDetailApiView,
    DiseaseListCreateApiView,
    DiseaseWhoDetailApiView,
    DiseaseWhoSearchApiView,
)


urlpatterns = [
    path('', DiseaseListCreateApiView.as_view(), name='disease_list_create'),
    path('<int:disease_id>/', DiseaseDetailApiView.as_view(), name='disease_detail'),
    path('who/search/', DiseaseWhoSearchApiView.as_view(), name='disease_who_search'),
    path('who/detail/', DiseaseWhoDetailApiView.as_view(), name='disease_who_detail'),
]
