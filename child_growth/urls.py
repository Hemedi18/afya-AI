from django.urls import path
from . import views

app_name = "child_growth"

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('add/', views.add_child, name='add_child'),
    path('child/<int:pk>/', views.child_detail, name='child_detail'),
    path('growth/<int:child_id>/', views.growth_chart, name='growth_chart'),
    path('milestones/<int:child_id>/', views.milestones, name='milestones'),
]
