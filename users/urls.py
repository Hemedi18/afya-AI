from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
from .settings_views import UserSettingsView
app_name = 'users'

urlpatterns = [
    path('register/', views.register, name='register'),
    path('onboarding/<int:step>/', views.onboarding, name='onboarding'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),
    path('settings/', UserSettingsView.as_view(), name='settings'),
    path('settings/<str:section>/', UserSettingsView.as_view(), name='settings_section'),
]