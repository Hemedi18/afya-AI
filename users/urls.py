from django.urls import path
from . import views
from .settings_views import UserSettingsView
app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('onboarding/<int:step>/', views.onboarding, name='onboarding'),
    path('login/', views.AfyaLoginView.as_view(), name='login'),
    path('social/<str:provider>/', views.social_login_redirect, name='social_login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('settings/', UserSettingsView.as_view(), name='settings'),
    path('settings/<str:section>/', UserSettingsView.as_view(), name='settings_section'),
]