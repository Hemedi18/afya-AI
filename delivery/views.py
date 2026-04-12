from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView
from .models import DeliveryAssignment

class DeliveryDashboardView(LoginRequiredMixin, ListView):
	model = DeliveryAssignment
	template_name = 'delivery/dashboard.html'
	context_object_name = 'assignments'
	queryset = DeliveryAssignment.objects.select_related('agent', 'sub_order__main_order', 'sub_order__pharmacy')

class DeliveryDetailView(LoginRequiredMixin, DetailView):
	model = DeliveryAssignment
	template_name = 'delivery/detail.html'
	context_object_name = 'assignment'
from django.shortcuts import render

# Create your views here.
