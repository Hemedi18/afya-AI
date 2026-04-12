from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, FormView
from django.urls import reverse_lazy
from .models import MedicineTemplate, PharmacyStock
from django.shortcuts import render, get_object_or_404
from django.contrib import messages
import csv
from django.db.models import Q, F
from django.db import transaction
from django.http import HttpResponseRedirect
from django.utils import timezone

class MedicineTemplateListView(ListView): # Removed LoginRequiredMixin
	model = MedicineTemplate
	template_name = 'inventory/medicine_list.html'
	context_object_name = 'medicines'
	
	def get_queryset(self):
		queryset = MedicineTemplate.objects.prefetch_related('pharmacy_stocks').all()
		q = self.request.GET.get('q')
		if q:
			queryset = queryset.filter(
				Q(generic_name__icontains=q) | 
				Q(brand__icontains=q) | 
				Q(category__icontains=q)
			)
		return queryset

class MedicineTemplateDetailView(DetailView): # Removed LoginRequiredMixin
	model = MedicineTemplate
	template_name = 'inventory/medicine_detail.html'
	context_object_name = 'medicine'

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		medicine = self.object
		# Show available stocks in different pharmacies
		context['available_stocks'] = PharmacyStock.objects.filter(
			medicine=medicine, quantity__gt=0, is_active=True
		).select_related('pharmacy')
		context['alternatives'] = []
		context['cheaper'] = []
		return context

class BulkStockUploadView(LoginRequiredMixin, UserPassesTestMixin, FormView):
	template_name = 'inventory/bulk_upload.html'
	success_url = reverse_lazy('inventory:medicine_list')

	def test_func(self):
		# Only pharmacy owners/managers can upload
		return self.request.user.groups.filter(name__in=["PharmacyOwner", "PharmacyManager"]).exists()

	def post(self, request, *args, **kwargs):
		csv_file = request.FILES.get('csv_file')
		if not csv_file:
			messages.error(request, "No file uploaded.")
			return self.form_invalid(None)
		decoded = csv_file.read().decode('utf-8').splitlines()
		reader = csv.DictReader(decoded)
		with transaction.atomic():
			count = 0
			for row in reader:
				try:
					med, _ = MedicineTemplate.objects.get_or_create(
						generic_name=row['generic_name'],
						brand=row['brand'],
						defaults={
							'category': row.get('category', ''),
							'description': row.get('description', ''),
							'requires_prescription': row.get('requires_prescription', 'False') == 'True',
							'side_effects': row.get('side_effects', ''),
						}
					)
					PharmacyStock.objects.create(
						pharmacy_id=row['pharmacy_id'],
						medicine=med,
						price=row['price'],
						quantity=row['quantity'],
						low_stock_threshold=row.get('low_stock_threshold', 5),
						batch_number=row['batch_number'],
						expiry_date=row['expiry_date'],
					)
					count += 1
				except Exception as e:
					messages.error(request, f"Error in row: {row} - {e}")
		messages.success(request, f"Successfully uploaded {count} stock items.")
		return HttpResponseRedirect(self.success_url)

def low_stock_alerts(request):
	# Show all low-stock and expiring soon items for the user's pharmacies
	stocks = PharmacyStock.objects.filter(
		pharmacy__owner=request.user,
		is_active=True
	).select_related('medicine', 'pharmacy')
	low_stock = [s for s in stocks if s.is_low_stock()]
	expiring_soon = [s for s in stocks if 0 <= (s.expiry_date - timezone.now().date()).days <= 30]
	return render(request, 'inventory/low_stock_alerts.html', {
		'low_stock': low_stock,
		'expiring_soon': expiring_soon,
	})
