from django.contrib import admin
from .models import MedicineTemplate, PharmacyStock
from django.utils.html import format_html

@admin.register(MedicineTemplate)
class MedicineTemplateAdmin(admin.ModelAdmin):
	list_display = ("generic_name", "brand", "category", "requires_prescription")
	search_fields = ("generic_name", "brand", "category")
	list_filter = ("category", "requires_prescription")

@admin.register(PharmacyStock)
class PharmacyStockAdmin(admin.ModelAdmin):
	list_display = ("pharmacy", "medicine", "price", "quantity", "low_stock_threshold", "expiry_date", "is_active", "is_low_stock_display", "is_expired_display")
	search_fields = ("pharmacy__name", "medicine__generic_name", "batch_number")
	list_filter = ("pharmacy", "medicine", "expiry_date", "is_active")

	def is_low_stock_display(self, obj):
		return format_html('<span style="color:{};font-weight:bold;">{}</span>',
			'red' if obj.is_low_stock() else 'green', obj.is_low_stock())
	is_low_stock_display.short_description = 'Low Stock?'
	is_low_stock_display.admin_order_field = 'quantity'

	def is_expired_display(self, obj):
		return format_html('<span style="color:{};font-weight:bold;">{}</span>',
			'red' if obj.is_expired() else 'green', obj.is_expired())
	is_expired_display.short_description = 'Expired?'
from django.contrib import admin

# Register your models here.
