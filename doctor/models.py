from django.conf import settings
from django.db import models
from django.utils import timezone

from menstrual.models import DoctorProfile


User = settings.AUTH_USER_MODEL


class DoctorVerificationRequest(models.Model):
	STATUS_PENDING = 'pending'
	STATUS_APPROVED = 'approved'
	STATUS_REJECTED = 'rejected'
	STATUS_CHOICES = [
		(STATUS_PENDING, 'Pending'),
		(STATUS_APPROVED, 'Approved'),
		(STATUS_REJECTED, 'Rejected'),
	]

	doctor_profile = models.OneToOneField(
		DoctorProfile,
		on_delete=models.CASCADE,
		related_name='verification_request',
	)
	license_number = models.CharField(max_length=120)
	issuing_body = models.CharField(max_length=150, blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	review_notes = models.TextField(blank=True)
	submitted_at = models.DateTimeField(auto_now_add=True)
	reviewed_at = models.DateTimeField(null=True, blank=True)
	reviewed_by = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='reviewed_doctor_requests',
	)

	class Meta:
		ordering = ['-submitted_at']

	def __str__(self):
		return f"Verification request for {self.doctor_profile.user.username}"

	def mark_approved(self, reviewer, notes=''):
		self.status = self.STATUS_APPROVED
		self.review_notes = notes
		self.reviewed_at = timezone.now()
		self.reviewed_by = reviewer
		self.save(update_fields=['status', 'review_notes', 'reviewed_at', 'reviewed_by'])
		profile = self.doctor_profile
		profile.verified = True
		profile.save(update_fields=['verified'])

	def mark_rejected(self, reviewer, notes=''):
		self.status = self.STATUS_REJECTED
		self.review_notes = notes
		self.reviewed_at = timezone.now()
		self.reviewed_by = reviewer
		self.save(update_fields=['status', 'review_notes', 'reviewed_at', 'reviewed_by'])
		profile = self.doctor_profile
		profile.verified = False
		profile.save(update_fields=['verified'])


class DoctorVerificationDocument(models.Model):
	verification_request = models.ForeignKey(
		DoctorVerificationRequest,
		on_delete=models.CASCADE,
		related_name='documents',
	)
	title = models.CharField(max_length=120, default='Medical License')
	document = models.FileField(upload_to='doctor_verifications/')
	uploaded_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-uploaded_at']

	def __str__(self):
		return f"{self.title} - {self.verification_request.doctor_profile.user.username}"
