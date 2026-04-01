from django.contrib import admin

from .models import DoctorVerificationDocument, DoctorVerificationRequest


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
