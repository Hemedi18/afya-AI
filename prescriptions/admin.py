from django.contrib import admin
from .models import Prescription

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
	list_display = ("user", "uploaded_at", "status")
	search_fields = ("user__username", "status")
	list_filter = ("status", "uploaded_at")

from django.contrib import admin

# Register your models here.
