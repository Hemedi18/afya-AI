from django.contrib import admin
from .models import UserAIPersona


@admin.register(UserAIPersona)
class UserAIPersonaAdmin(admin.ModelAdmin):
	list_display = ('user', 'age', 'gender', 'stress_level', 'exercise_frequency', 'onboarding_complete', 'updated_at')
	list_filter = ('gender', 'stress_level', 'exercise_frequency')
	search_fields = ('user__username', 'user__email', 'health_notes', 'goals', 'permanent_diseases')
	autocomplete_fields = ('user',)
