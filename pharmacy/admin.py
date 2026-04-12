from django.contrib import admin
from .models import Pharmacy, PharmacyStaff, PharmacyLocation
from django.contrib import admin

@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "license_number", "is_verified", "is_open_24_7", "commission_rate", "wallet_balance", "rating", "created_at")
    search_fields = ("name", "license_number", "owner__username")
    list_filter = ("is_verified", "is_open_24_7", "created_at")

@admin.register(PharmacyLocation)
class PharmacyLocationAdmin(admin.ModelAdmin):
    list_display = ("pharmacy", "address", "city", "delivery_radius_km")
    search_fields = ("pharmacy__name", "address", "city")
    list_filter = ("city",)

@admin.register(PharmacyStaff)
class PharmacyStaffAdmin(admin.ModelAdmin):
    list_display = ("pharmacy", "user", "role", "created_at")
    search_fields = ("pharmacy__name", "user__username", "role")
    list_filter = ("role", "created_at")
from django.contrib import admin

# Register your models here.
