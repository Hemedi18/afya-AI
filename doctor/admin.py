from django.contrib import admin

from .models import (
	DoctorFollow,
	DoctorRating,
	DoctorReport,
	DoctorVerificationDocument,
	DoctorVerificationRequest,
	PatientLog,
	PatientLogEntry,
	PatientLogField,
)


class DoctorVerificationDocumentInline(admin.TabularInline):
	model = DoctorVerificationDocument
	extra = 0


@admin.register(DoctorVerificationRequest)
class DoctorVerificationRequestAdmin(admin.ModelAdmin):
	list_display = ('doctor_profile', 'license_number', 'status', 'submitted_at', 'reviewed_by')
	list_filter = ('status', 'submitted_at')
	search_fields = ('doctor_profile__user__username', 'license_number', 'issuing_body')
	autocomplete_fields = ('doctor_profile', 'reviewed_by')
	inlines = [DoctorVerificationDocumentInline]


@admin.register(DoctorVerificationDocument)
class DoctorVerificationDocumentAdmin(admin.ModelAdmin):
	list_display = ('title', 'verification_request', 'uploaded_at')
	search_fields = ('title', 'verification_request__doctor_profile__user__username')
	autocomplete_fields = ('verification_request',)


@admin.register(DoctorFollow)
class DoctorFollowAdmin(admin.ModelAdmin):
	list_display = ('follower', 'doctor_profile', 'created_at')
	search_fields = ('follower__username', 'doctor_profile__user__username')
	autocomplete_fields = ('follower', 'doctor_profile')


@admin.register(DoctorRating)
class DoctorRatingAdmin(admin.ModelAdmin):
	list_display = ('doctor_profile', 'rater', 'score', 'created_at')
	list_filter = ('score', 'created_at')
	search_fields = ('doctor_profile__user__username', 'rater__username', 'note')
	autocomplete_fields = ('doctor_profile', 'rater')


@admin.register(DoctorReport)
class DoctorReportAdmin(admin.ModelAdmin):
	list_display = ('doctor_profile', 'reporter', 'reason', 'created_at')
	list_filter = ('created_at',)
	search_fields = ('doctor_profile__user__username', 'reporter__username', 'reason', 'details')
	autocomplete_fields = ('doctor_profile', 'reporter')


class PatientLogFieldInline(admin.TabularInline):
	model = PatientLogField
	extra = 0
	fields = ('field_label', 'field_type', 'placeholder', 'required', 'order')


@admin.register(PatientLog)
class PatientLogAdmin(admin.ModelAdmin):
	list_display = ('title', 'doctor', 'patient', 'is_sent', 'is_active', 'created_at')
	list_filter = ('is_sent', 'is_active', 'created_at')
	search_fields = ('title', 'doctor__username', 'patient__username')
	inlines = [PatientLogFieldInline]


@admin.register(PatientLogField)
class PatientLogFieldAdmin(admin.ModelAdmin):
	list_display = ('field_label', 'field_type', 'log', 'required', 'order')
	list_filter = ('field_type', 'required')
	search_fields = ('field_label', 'log__title')


@admin.register(PatientLogEntry)
class PatientLogEntryAdmin(admin.ModelAdmin):
	list_display = ('log', 'submitted_by', 'submitted_at')
	list_filter = ('submitted_at',)
	search_fields = ('log__title', 'submitted_by__username')
