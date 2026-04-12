from django.contrib import admin
from .models import Order, SubOrder, OrderItem

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ("user", "total_amount", "payment_status", "created_at")
	search_fields = ("user__username", "payment_status")
	list_filter = ("payment_status", "created_at")

@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
	list_display = ("id", "main_order", "pharmacy", "sub_total", "status", "created_at")
	list_filter = ("status", "pharmacy", "created_at")
	search_fields = ("main_order__id", "pharmacy__name")

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = ("sub_order", "stock_item", "quantity", "price_at_purchase")
	search_fields = ("sub_order__main_order__user__username", "stock_item__medicine__generic_name")
	list_filter = ("sub_order__status",)
	readonly_fields = ("price_at_purchase",)
