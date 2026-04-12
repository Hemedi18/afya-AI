from django.contrib import admin
from .models import Cart, CartItem, Order, SubOrder, OrderItem

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
	list_display = ("user", "created_at")
	search_fields = ("user__username",)
	list_filter = ("created_at",)

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
	list_display = ("cart", "stock", "quantity")
	search_fields = ("cart__user__username", "stock__medicine__generic_name")
	list_filter = ("cart",)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = ("user", "total_amount", "payment_status", "created_at")
	search_fields = ("user__username",)
	list_filter = ("payment_status", "created_at")

@admin.register(SubOrder)
class SubOrderAdmin(admin.ModelAdmin):
	list_display = ("main_order", "pharmacy", "sub_total", "status", "created_at")
	search_fields = ("main_order__id", "pharmacy__name")
	list_filter = ("status", "pharmacy")

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
	list_display = ("sub_order", "stock_item", "quantity", "price_at_time_of_purchase")
	search_fields = ("sub_order__id", "stock_item__medicine__generic_name")
	list_filter = ("sub_order",)
from django.contrib import admin

# Register your models here.
