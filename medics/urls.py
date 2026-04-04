from django.urls import path

from .views import medication_browser, medication_detail


app_name = 'medics'

urlpatterns = [
    path('', medication_browser, name='browse'),
    path('<int:medication_id>/', medication_detail, name='detail'),
]
