import json
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from .models import Pharmacy, PharmacyLocation, PharmacyStaff
from inventory.models import PharmacyStock
from orders.models import SubOrder
from AI_brain.pharmacy_ai import suggest_cheaper_generics
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.utils import timezone
from django.db import models
from prescriptions.models import Prescription

class PharmacyDashboardView(LoginRequiredMixin, ListView):
	model = Pharmacy
	template_name = 'pharmacy/dashboard.html'
	context_object_name = 'pharmacies'
	# Improved query to get location for city display
	queryset = Pharmacy.objects.select_related('owner', 'location').all()

class PharmacyRegisterView(LoginRequiredMixin, CreateView):
	model = Pharmacy
	fields = ['name', 'license_number', 'commission_rate']
	template_name = 'pharmacy/register.html'
	success_url = reverse_lazy('pharmacy:dashboard')

class PharmacyDetailView(LoginRequiredMixin, DetailView):
	model = Pharmacy
	template_name = 'pharmacy/detail.html'
	context_object_name = 'pharmacy'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		pharmacy = self.object
		query = self.request.GET.get('q', '').strip()
		stocks = PharmacyStock.objects.filter(pharmacy=pharmacy, is_active=True).select_related('medicine')
		if query:
			stocks = stocks.filter(medicine__generic_name__icontains=query)
		stocks = stocks.filter(quantity__gt=0).order_by('medicine__generic_name')
		# AI suggestions: suggest cheaper generics for the first medicine in stock
		ai_suggestions = []
		if stocks.exists():
			ai_suggestions = suggest_cheaper_generics(stocks.first().medicine)
		context.update({
			'stocks': stocks,
			'query': query,
			'ai_suggestions': ai_suggestions,
		})
		return context

class PharmacyStaffDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Dashboard for pharmacy owners and staff to manage orders and stock."""
    template_name = 'pharmacy/staff_dashboard.html'
    context_object_name = 'orders'

    def test_func(self):
        return Pharmacy.objects.filter(owner=self.request.user).exists() or \
               PharmacyStaff.objects.filter(user=self.request.user).exists()

    def get_queryset(self):
        # Get pharmacies managed by this user
        if Pharmacy.objects.filter(owner=self.request.user).exists():
            managed_pharmacies = Pharmacy.objects.filter(owner=self.request.user)
        else:
            managed_pharmacies = Pharmacy.objects.filter(staff__user=self.request.user)
        
        queryset = SubOrder.objects.filter(pharmacy__in=managed_pharmacies).order_by('-created_at')
        
        # Filtering Logic
        q = self.request.GET.get('q')
        status_filter = self.request.GET.get('status_filter')
        
        if q:
            queryset = queryset.filter(
                Q(main_order__user__username__icontains=q) |
                Q(main_order__id__icontains=q)
            )
        if status_filter:
            queryset = queryset.filter(status=status_filter)
            
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pharmacies = Pharmacy.objects.filter(Q(owner=self.request.user) | Q(staff__user=self.request.user)).distinct()
        context['pharmacies'] = pharmacies
        context['low_stock'] = PharmacyStock.objects.filter(
            pharmacy__in=pharmacies,
            quantity__lte=models.F('low_stock_threshold')
        ).select_related('medicine')

        # Weekly trends data for chart
        today = timezone.now().date()
        seven_days_ago = today - timezone.timedelta(days=6)
        trends = SubOrder.objects.filter(
            pharmacy__in=pharmacies,
            created_at__date__gte=seven_days_ago
        ).annotate(
            day=models.functions.TruncDate('created_at')
        ).values('day').annotate(
            count=models.Count('id')
        ).order_by('day')

        trend_map = {t['day']: t['count'] for t in trends}
        labels, values = [], []
        for i in range(7):
            d = seven_days_ago + timezone.timedelta(days=i)
            labels.append(d.strftime('%a'))
            values.append(trend_map.get(d, 0))

        context['sales_labels'] = json.dumps(labels)
        context['sales_data'] = json.dumps(values)

        # Monthly Revenue trends (Last 30 days)
        thirty_days_ago = today - timezone.timedelta(days=29)
        revenue_trends = SubOrder.objects.filter(
            pharmacy__in=pharmacies,
            created_at__date__gte=thirty_days_ago,
            status='delivered'
        ).annotate(
            day=models.functions.TruncDate('created_at')
        ).values('day').annotate(
            total=models.Sum('sub_total')
        ).order_by('day')

        rev_map = {t['day']: float(t['total']) for t in revenue_trends}
        rev_labels, rev_values = [], []
        for i in range(30):
            d = thirty_days_ago + timezone.timedelta(days=i)
            rev_labels.append(d.strftime('%d %b'))
            rev_values.append(rev_map.get(d, 0))

        context['rev_labels'] = json.dumps(rev_labels)
        context['rev_data'] = json.dumps(rev_values)

        context['pending_prescriptions'] = Prescription.objects.filter(
            status='pending',
            order__suborders__pharmacy__in=pharmacies
        ).distinct().select_related('user', 'order')
        context['status_choices'] = SubOrder.STATUS_CHOICES
        return context

class SubOrderUpdateStatusView(LoginRequiredMixin, View):
    """Quick action to update sub-order status."""
    def post(self, request, pk):
        sub_order = get_object_or_404(SubOrder, pk=pk)
        # Basic security check: user must own/work at this pharmacy
        is_owner = sub_order.pharmacy.owner == request.user
        is_staff = PharmacyStaff.objects.filter(pharmacy=sub_order.pharmacy, user=request.user).exists()
        
        if is_owner or is_staff:
            new_status = request.POST.get('status')
            sub_order.status = new_status
            sub_order.save()
            messages.success(request, f"Order #{sub_order.id} updated to {new_status}")
        return redirect('pharmacy:staff_dashboard')
