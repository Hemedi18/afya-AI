from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CommunityGroup,
    CommunityPost,
    CommunityReply,
    CommunityStatus,
    DailyLog,
    DailyTip,
    DoctorProfile,
    MenstrualCycle,
    MenstrualUserSetting,
    Reminder,
)


admin.site.site_header = "ZanzHub AI Health Admin"
admin.site.site_title = "ZanzHub Admin"
admin.site.index_title = "Control every part of the platform"


class DailyLogInline(admin.TabularInline):
    model = DailyLog
    extra = 0
    fields = ('date', 'flow_intensity', 'flow_notes', 'ai_suggestion')
    readonly_fields = ('ai_suggestion',)


class CommunityReplyInline(admin.TabularInline):
    model = CommunityReply
    extra = 0
    fields = ('user', 'content', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(MenstrualCycle)
class MenstrualCycleAdmin(admin.ModelAdmin):
    list_display = ('user', 'start_date', 'expected_end_date', 'is_active', 'elapsed_days_display')
    list_filter = ('is_active', 'start_date', 'expected_end_date')
    search_fields = ('user__username', 'user__email')
    autocomplete_fields = ('user',)
    inlines = [DailyLogInline]

    def elapsed_days_display(self, obj):
        return obj.elapsed_days
    elapsed_days_display.short_description = 'Cycle Day'


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ('cycle', 'date', 'flow_intensity', 'symptoms_count', 'has_ai_suggestion')
    list_filter = ('date', 'flow_intensity')
    search_fields = ('cycle__user__username', 'flow_notes', 'ai_suggestion')
    autocomplete_fields = ('cycle',)
    readonly_fields = ('ai_suggestion',)

    def symptoms_count(self, obj):
        return len(obj.physical_symptoms or [])
    symptoms_count.short_description = 'Symptoms'

    def has_ai_suggestion(self, obj):
        return bool(obj.ai_suggestion)
    has_ai_suggestion.boolean = True
    has_ai_suggestion.short_description = 'AI Insight'


@admin.register(DailyTip)
class DailyTipAdmin(admin.ModelAdmin):
    list_display = ('title', 'source', 'date_created', 'has_source_url')
    list_filter = ('source', 'date_created')
    search_fields = ('title', 'content', 'url')
    filter_horizontal = ('saved_permanent',)

    def has_source_url(self, obj):
        return bool(obj.url)
    has_source_url.boolean = True
    has_source_url.short_description = 'Verified URL'


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'audience_gender', 'is_anonymous', 'short_content', 'created_at', 'likes_count', 'has_media')
    list_filter = ('audience_gender', 'is_anonymous', 'created_at',)
    search_fields = ('user__username', 'content')
    autocomplete_fields = ('user',)
    filter_horizontal = ('groups',)
    inlines = [CommunityReplyInline]

    def short_content(self, obj):
        return (obj.content[:60] + '...') if len(obj.content) > 60 else obj.content
    short_content.short_description = 'Content'

    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = 'Likes'

    def has_media(self, obj):
        return bool(obj.image or obj.video)
    has_media.boolean = True
    has_media.short_description = 'Media'

@admin.register(CommunityReply)
class CommunityReplyAdmin(admin.ModelAdmin):
    list_display = ('post', 'parent', 'user', 'short_content', 'created_at', 'likes_count', 'dislikes_count')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'content', 'post__content')
    autocomplete_fields = ('post', 'user')

    def short_content(self, obj):
        return (obj.content[:60] + '...') if len(obj.content) > 60 else obj.content
    short_content.short_description = 'Reply'

    def likes_count(self, obj):
        return obj.likes.count()
    likes_count.short_description = 'Likes'

    def dislikes_count(self, obj):
        return obj.dislikes.count()
    dislikes_count.short_description = 'Dislikes'


@admin.register(CommunityGroup)
class CommunityGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'audience_gender', 'created_by', 'members_count', 'created_at')
    list_filter = ('audience_gender', 'created_at')
    search_fields = ('name', 'description', 'created_by__username')
    autocomplete_fields = ('created_by',)
    filter_horizontal = ('members',)

    def members_count(self, obj):
        return obj.members.count()
    members_count.short_description = 'Members'


@admin.register(CommunityStatus)
class CommunityStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'group', 'audience_gender', 'short_content', 'created_at', 'expires_at')
    list_filter = ('audience_gender', 'created_at', 'expires_at')
    search_fields = ('user__username', 'content', 'group__name')
    autocomplete_fields = ('user', 'group')

    def short_content(self, obj):
        return (obj.content[:50] + '...') if len(obj.content) > 50 else obj.content
    short_content.short_description = 'Status'


@admin.action(description='Verify selected doctors')
def verify_doctors(modeladmin, request, queryset):
    queryset.update(verified=True)


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ('doctor_name', 'gender', 'specialization', 'hospital_name', 'verified_badge')
    list_filter = ('verified', 'gender', 'specialization', 'hospital_name')
    search_fields = ('user__username', 'user__email', 'specialization', 'hospital_name', 'bio')
    autocomplete_fields = ('user',)
    actions = [verify_doctors]
    fieldsets = (
        ('Doctor account', {
            'fields': ('user', 'verified'),
            'description': 'Admin anaweza kusajili doctor mpya kwa kuchagua user account kisha kuweka profile details hapa.'
        }),
        ('Professional details', {
            'fields': ('specialization', 'hospital_name', 'bio'),
        }),
    )

    def doctor_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    doctor_name.short_description = 'Doctor'

    def verified_badge(self, obj):
        color = '#198754' if obj.verified else '#6c757d'
        label = 'Verified' if obj.verified else 'Pending'
        return format_html('<span style="background:{};color:white;padding:4px 10px;border-radius:999px;">{}</span>', color, label)
    verified_badge.short_description = 'Status'


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'event_date', 'reminder_time', 'is_notified')
    list_filter = ('is_notified', 'event_date')
    search_fields = ('user__username', 'title')
    autocomplete_fields = ('user',)


@admin.register(MenstrualUserSetting)
class MenstrualUserSettingAdmin(admin.ModelAdmin):
    list_display = ('user', 'color_theme', 'privacy_mode', 'anonymous_mode', 'emergency_alerts_enabled', 'reminder_period', 'reminder_ovulation', 'reminder_fertile_window', 'updated_at')
    list_filter = ('color_theme', 'privacy_mode', 'anonymous_mode', 'emergency_alerts_enabled', 'reminder_period', 'reminder_ovulation', 'reminder_fertile_window')
    search_fields = ('user__username', 'user__email')
    autocomplete_fields = ('user',)
