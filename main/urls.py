from django.urls import path
from . import views
app_name = 'main'
# Hapa ndipo kosa lilipo: Hakikisha jina ni 'urlpatterns'
urlpatterns = [
    path('', views.home, name='home'),
    path('services/', views.services, name='services'),
    path('male-dashboard/', views.male_dashboard, name='male_dashboard'),
    path('control-center/', views.AdminControlCenterView.as_view(), name='control_center'),
    path('about/', views.about, name='about'),
    path('contact/', views.contact, name='contact'),
    path('documentation/', views.documentation, name='documentation'),
]