from django.urls import path

from . import views

app_name = 'reproduction'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('checks/new/', views.create_check, name='create_check'),
    path('goals/new/', views.create_goal, name='create_goal'),
    path('goals/<int:goal_id>/toggle/', views.toggle_goal_today, name='toggle_goal_today'),
    path('findings/new/', views.create_finding, name='create_finding'),
    path('metrics/new/', views.create_metric, name='create_metric'),
    path('couples/connect/', views.connect_couple, name='connect_couple'),
]
