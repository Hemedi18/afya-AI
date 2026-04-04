from django.conf import settings
from django.db import models
from django.utils import timezone


class FaceEnrollment(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='face_enrollment')
	reference_image = models.ImageField(upload_to='face_enrollment/reference/')
	embedding = models.JSONField(default=list, blank=True)
	embedding_version = models.CharField(max_length=32, default='v1')
	active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	last_verified_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ['-updated_at']

	def __str__(self):
		return f"FaceEnrollment<{self.user_id}>"


class FaceScanAudit(models.Model):
	PURPOSE_CARD_ACCESS = 'card_access'
	PURPOSE_ADMIN_LOOKUP = 'admin_lookup'
	PURPOSE_CHOICES = [
		(PURPOSE_CARD_ACCESS, 'Card Access Verification'),
		(PURPOSE_ADMIN_LOOKUP, 'Admin/Doctor Lookup'),
	]

	scanner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='face_scans_performed')
	matched_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='face_scans_matched')
	purpose = models.CharField(max_length=32, choices=PURPOSE_CHOICES)
	similarity = models.FloatField(default=0.0)
	success = models.BooleanField(default=False)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(default=timezone.now)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		status = 'ok' if self.success else 'fail'
		return f"FaceScanAudit<{self.purpose}:{status}>"
