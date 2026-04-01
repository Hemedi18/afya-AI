from django.urls import path

from . import views

app_name = 'card'

urlpatterns = [
    path('', views.card_home, name='home'),
    path('details/', views.card_details, name='details'),
    path('notifications/', views.card_notifications, name='notifications'),
    path('public/<uuid:token>/', views.public_profile, name='public_profile'),
]
