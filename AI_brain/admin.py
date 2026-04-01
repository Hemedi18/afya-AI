from django.contrib import admin
from .models import AIInteractionLog


@admin.register(AIInteractionLog)
class AIInteractionLogAdmin(admin.ModelAdmin):
	list_display = ('user', 'persona_completeness', 'identity_verified', 'medical_info_verified', 'created_at')
	list_filter = ('identity_verified', 'medical_info_verified', 'created_at')
	search_fields = ('user__username', 'question', 'reply')
	autocomplete_fields = ('user',)
