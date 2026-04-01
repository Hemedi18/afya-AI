from django.contrib import admin
from .models import OfflineConversation, OfflineMessage, SmsWebhookLog


@admin.register(OfflineConversation)
class OfflineConversationAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'title', 'model_name', 'is_active', 'updated_at')
	list_filter = ('is_active', 'model_name', 'created_at')
	search_fields = ('title', 'user__username')


@admin.register(OfflineMessage)
class OfflineMessageAdmin(admin.ModelAdmin):
	list_display = ('id', 'conversation', 'role', 'created_at')
	list_filter = ('role', 'created_at')
	search_fields = ('content', 'conversation__user__username')


@admin.register(SmsWebhookLog)
class SmsWebhookLogAdmin(admin.ModelAdmin):
	list_display = ('id', 'sender', 'outbound_sent', 'created_at')
	list_filter = ('outbound_sent', 'created_at')
	search_fields = ('sender', 'message_text', 'reply_text', 'outbound_detail')
	readonly_fields = ('sender', 'message_text', 'reply_text', 'outbound_sent', 'outbound_detail', 'raw_payload', 'created_at')
