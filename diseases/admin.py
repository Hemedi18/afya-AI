from django.contrib import admin

from .models import Disease


@admin.register(Disease)
class DiseaseAdmin(admin.ModelAdmin):
	list_display = ('name', 'icd_code', 'updated_at')
	list_filter = ('created_at', 'updated_at')
	search_fields = ('name', 'icd_code', 'definition', 'symptoms', 'prevention', 'treatment')
	ordering = ('name',)
