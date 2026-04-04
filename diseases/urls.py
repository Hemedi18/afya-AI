from django.urls import path

from .views import disease_browser, disease_detail


app_name = 'diseases'

urlpatterns = [
    path('', disease_browser, name='browse'),
    path('<int:disease_id>/', disease_detail, name='detail'),
]
