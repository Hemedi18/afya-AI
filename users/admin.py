from django.contrib import admin
from .models import UserAIPersona, PersonaDataSnapshot


@admin.register(UserAIPersona)
class UserAIPersonaAdmin(admin.ModelAdmin):
	list_display = (
		'user', 'birth_date', 'age', 'gender', 'stress_level', 'exercise_frequency', 'onboarding_complete',
		'profile_completeness_score', 'identity_verified', 'medical_info_verified', 'updated_at',
	)
	list_filter = ('gender', 'stress_level', 'exercise_frequency', 'identity_verified', 'medical_info_verified')
	search_fields = ('user__username', 'user__email', 'health_notes', 'goals', 'permanent_diseases')
	autocomplete_fields = ('user',)


@admin.register(PersonaDataSnapshot)
class PersonaDataSnapshotAdmin(admin.ModelAdmin):
	list_display = ('user', 'source', 'completeness_score', 'identity_verified', 'medical_info_verified', 'created_at')
	list_filter = ('source', 'identity_verified', 'medical_info_verified', 'created_at')
	search_fields = ('user__username', 'user__email')
	autocomplete_fields = ('user', 'persona')
