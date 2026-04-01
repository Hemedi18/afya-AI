from django.contrib import admin
from .models import AIScoreSnapshot, CoupleConnection, PubertyCheckRecord, PubertyFinding, PubertyHabitGoal, PubertyPreventionPlanDay, ReproductiveMetricEntry


@admin.register(PubertyCheckRecord)
class PubertyCheckRecordAdmin(admin.ModelAdmin):
	list_display = ('user', 'age', 'gender', 'risk_level', 'needs_doctor', 'created_at')
	list_filter = ('risk_level', 'gender', 'needs_doctor', 'created_at')
	search_fields = ('user__username', 'notes', 'ai_guidance')
	readonly_fields = ('red_flags',)


@admin.register(PubertyHabitGoal)
class PubertyHabitGoalAdmin(admin.ModelAdmin):
	list_display = ('user', 'title', 'target_days', 'streak_days', 'completed_today', 'updated_at')
	list_filter = ('completed_today', 'updated_at')
	search_fields = ('user__username', 'title', 'details')


@admin.register(PubertyFinding)
class PubertyFindingAdmin(admin.ModelAdmin):
	list_display = ('user', 'title', 'share_to_community', 'community_post', 'created_at')
	list_filter = ('share_to_community', 'is_anonymous', 'created_at')
	search_fields = ('user__username', 'title', 'finding', 'tags')


@admin.register(PubertyPreventionPlanDay)
class PubertyPreventionPlanDayAdmin(admin.ModelAdmin):
	list_display = ('check_record', 'day_number', 'title', 'is_done', 'created_at')
	list_filter = ('is_done', 'created_at')
	search_fields = ('check_record__user__username', 'title', 'action')


@admin.register(ReproductiveMetricEntry)
class ReproductiveMetricEntryAdmin(admin.ModelAdmin):
	list_display = ('user', 'category', 'metric_key', 'metric_value', 'recorded_at')
	list_filter = ('category', 'recorded_at')
	search_fields = ('user__username', 'metric_key', 'notes')


@admin.register(AIScoreSnapshot)
class AIScoreSnapshotAdmin(admin.ModelAdmin):
	list_display = ('user', 'overall_score', 'fertility_score', 'sexual_performance_score', 'hormone_balance_score', 'stress_libido_score', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('user__username', 'summary')


@admin.register(CoupleConnection)
class CoupleConnectionAdmin(admin.ModelAdmin):
	list_display = ('requester', 'partner', 'status', 'updated_at')
	list_filter = ('status', 'updated_at')
	search_fields = ('requester__username', 'partner__username')
