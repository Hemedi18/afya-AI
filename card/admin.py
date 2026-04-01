from django.contrib import admin

from .models import CardNotification, HealthCard, PersonaReminderConfig


@admin.register(HealthCard)
class HealthCardAdmin(admin.ModelAdmin):
	list_display = ('user', 'public_token', 'updated_at')
	search_fields = ('user__username', 'user__first_name', 'user__last_name')
	readonly_fields = ('public_token', 'updated_at')


@admin.register(PersonaReminderConfig)
class PersonaReminderConfigAdmin(admin.ModelAdmin):
	list_display = ('user', 'interval_days', 'reminder_cooldown_days', 'last_notified_at', 'updated_at')
	search_fields = ('user__username',)


@admin.register(CardNotification)
class CardNotificationAdmin(admin.ModelAdmin):
	list_display = ('user', 'kind', 'title', 'is_read', 'created_at')
	list_filter = ('kind', 'is_read', 'created_at')
	search_fields = ('user__username', 'title', 'body')
