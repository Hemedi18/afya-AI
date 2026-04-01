from django.contrib import admin

from .models import ClarificationMessage, ClarificationRequest, ContentReport, PrivateConversation, PrivateMessage


class PrivateMessageInline(admin.TabularInline):
	model = PrivateMessage
	extra = 0
	readonly_fields = ('created_at',)


@admin.register(PrivateConversation)
class PrivateConversationAdmin(admin.ModelAdmin):
	list_display = ('subject', 'patient', 'doctor', 'is_closed', 'updated_at')
	list_filter = ('is_closed', 'updated_at')
	search_fields = ('subject', 'patient__username', 'doctor__username')
	autocomplete_fields = ('patient', 'doctor')
	inlines = [PrivateMessageInline]


@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
	list_display = ('conversation', 'sender', 'created_at', 'is_read')
	list_filter = ('is_read', 'created_at')
	search_fields = ('conversation__subject', 'sender__username', 'content')
	autocomplete_fields = ('conversation', 'sender')


@admin.register(ContentReport)
class ContentReportAdmin(admin.ModelAdmin):
	list_display = ('reporter', 'reason', 'status', 'created_at', 'reviewed_by')
	list_filter = ('status', 'created_at')
	search_fields = ('reporter__username', 'reason', 'details')
	autocomplete_fields = ('reporter', 'post', 'comment', 'reviewed_by')


@admin.register(ClarificationRequest)
class ClarificationRequestAdmin(admin.ModelAdmin):
	list_display = ('asker', 'target_role', 'target_doctor', 'status', 'created_at', 'responded_by')
	list_filter = ('target_role', 'status', 'created_at')
	search_fields = ('asker__username', 'question', 'response')
	autocomplete_fields = ('asker', 'post', 'comment', 'target_doctor', 'responded_by')
	filter_horizontal = ('likes', 'dislikes')


@admin.register(ClarificationMessage)
class ClarificationMessageAdmin(admin.ModelAdmin):
	list_display = ('clarification', 'user', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('clarification__question', 'user__username', 'content')
	autocomplete_fields = ('clarification', 'user')
