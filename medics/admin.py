from django.contrib import admin

from .models import Medication


@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
	list_display = ('name', 'generic_name', 'manufacturer', 'rx_required', 'updated_at')
	list_filter = ('rx_required', 'created_at', 'updated_at')
	search_fields = ('name', 'generic_name', 'manufacturer', 'active_ingredients', 'description')
	ordering = ('name',)
