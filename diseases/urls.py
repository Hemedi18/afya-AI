from django.urls import path
from . import views

app_name = 'diseases'

urlpatterns = [
    path('browse/', views.DiseaseSearchView.as_view(), name='browse'),
    path('dashboard/', views.DiseaseDashboardView.as_view(), name='user_dashboard'),
    path('search/', views.DiseaseSearchView.as_view(), name='search'),
    path('add/<int:disease_id>/', views.AddUserDiseaseView.as_view(), name='add_disease'),
    path('log/<int:user_disease_id>/', views.LogDiseaseMetricsView.as_view(), name='log_metrics'),
    path('timeline/<int:user_disease_id>/', views.DiseaseTimelineView.as_view(), name='timeline'), # Existing path
    path('wiki_search/', views.DiseaseWikiSearchView.as_view(), name='wiki_search'), # New path for external search
]