from django.contrib import admin
from .models import DeliveryAgent, DeliveryAssignment
from django.contrib import admin

@admin.register(DeliveryAgent)
class DeliveryAgentAdmin(admin.ModelAdmin):
	list_display = ("user", "vehicle_type", "vehicle_reg", "is_online")
	search_fields = ("user__username", "vehicle_type", "vehicle_reg")
	list_filter = ("is_online",)

@admin.register(DeliveryAssignment)
class DeliveryAssignmentAdmin(admin.ModelAdmin):
	list_display = ("sub_order", "agent", "pickup_time", "delivery_time", "status")
	search_fields = ("sub_order__id", "agent__user__username")
	list_filter = ("status",)
from django.contrib import admin

# Register your models here.
