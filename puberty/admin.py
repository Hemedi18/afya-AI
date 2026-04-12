from django.contrib import admin
from .models import PubertyProfile, PubertyQuestion, PubertyAnswer, PubertyGuide, PubertyTip

@admin.register(PubertyProfile)
class PubertyProfileAdmin(admin.ModelAdmin):
	list_display = ("user", "gender", "age", "puberty_stage", "country", "created_at")
	search_fields = ("user__username", "country", "puberty_stage")
	list_filter = ("gender", "country", "puberty_stage")

@admin.register(PubertyQuestion)
class PubertyQuestionAdmin(admin.ModelAdmin):
	list_display = ('question', 'category', 'gender_specific', 'age_group')
	search_fields = ('question',)
	list_filter = ('category', 'gender_specific', 'age_group')

@admin.register(PubertyAnswer)
class PubertyAnswerAdmin(admin.ModelAdmin):
	list_display = ('user', 'question', 'created_at')
	search_fields = ('user__username', 'question__question')
	list_filter = ('created_at',)

@admin.register(PubertyGuide)
class PubertyGuideAdmin(admin.ModelAdmin):
	list_display = ('title', 'gender', 'age_group')
	search_fields = ('title', 'description')
	list_filter = ('gender', 'age_group')

@admin.register(PubertyTip)
class PubertyTipAdmin(admin.ModelAdmin):
	list_display = ('title', 'category', 'priority')
	search_fields = ('title', 'content')
	list_filter = ('category', 'priority')
