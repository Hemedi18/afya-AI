from django.urls import path
from . import views

app_name = 'puberty'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('assessment/', views.assessment, name='assessment'),
    path('chat/', views.chat, name='chat'),
    path('guides/', views.guides, name='guides'),
    path('guide/<int:guide_id>/', views.guide_detail, name='guide_detail'),
    path('profile/', views.profile, name='profile'),
]