
from django.contrib import admin
from .models import Child, GrowthRecord, DevelopmentMilestone, ChildMilestone, NutritionTip, Vaccination, ChildVaccination

@admin.register(Child)
class ChildAdmin(admin.ModelAdmin):
	list_display = ("name", "user", "gender", "birth_date", "birth_weight", "birth_height", "blood_group", "created_at")
	search_fields = ("name", "user__username")
	list_filter = ("gender", "blood_group", "created_at")
	ordering = ("-created_at",)

@admin.register(GrowthRecord)
class GrowthRecordAdmin(admin.ModelAdmin):
	list_display = ("child", "weight", "height", "head_circumference", "recorded_at")
	search_fields = ("child__name",)
	list_filter = ("recorded_at",)
	ordering = ("-recorded_at",)

@admin.register(DevelopmentMilestone)
class DevelopmentMilestoneAdmin(admin.ModelAdmin):
	list_display = ("title", "age_range")
	search_fields = ("title", "age_range")
	ordering = ("age_range", "title")

@admin.register(ChildMilestone)
class ChildMilestoneAdmin(admin.ModelAdmin):
	list_display = ("child", "milestone", "achieved", "achieved_date")
	search_fields = ("child__name", "milestone__title")
	list_filter = ("achieved", "achieved_date")
	ordering = ("-achieved_date",)

@admin.register(NutritionTip)
class NutritionTipAdmin(admin.ModelAdmin):
	list_display = ("title", "age_group")
	search_fields = ("title", "age_group")
	ordering = ("age_group", "title")

@admin.register(Vaccination)
class VaccinationAdmin(admin.ModelAdmin):
	list_display = ("name", "age_due")
	search_fields = ("name", "age_due")
	ordering = ("age_due", "name")

@admin.register(ChildVaccination)
class ChildVaccinationAdmin(admin.ModelAdmin):
	list_display = ("child", "vaccination", "completed", "completed_date")
	search_fields = ("child__name", "vaccination__name")
	list_filter = ("completed", "completed_date")
	ordering = ("-completed_date",)
from django.contrib import admin

# Register your models here.
