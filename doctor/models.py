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


class DoctorFollow(models.Model):
	follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followed_doctors')
	doctor_profile = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='followers')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		unique_together = ('follower', 'doctor_profile')

	def __str__(self):
		return f"{self.follower} follows Dr. {self.doctor_profile.user.username}"


class DoctorRating(models.Model):
	rater = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_ratings', db_column='user_id')
	doctor_profile = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='ratings', db_column='doctor_id')
	score = models.PositiveSmallIntegerField(default=5, db_column='rating')
	note = models.TextField(blank=True, db_column='comment')
	date = models.DateField(default=timezone.localdate, db_column='date')
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.score}/5 by {self.rater} for Dr. {self.doctor_profile.user.username}"


class DoctorReport(models.Model):
	reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_reports', db_column='user_id')
	doctor_profile = models.ForeignKey(DoctorProfile, on_delete=models.CASCADE, related_name='reports', db_column='doctor_id')
	reason = models.CharField(max_length=50)
	details = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Report by {self.reporter} on Dr. {self.doctor_profile.user.username}"


# ─────────────────────────────────────────────────────────────────────────────
# PATIENT LOG SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

class PatientLog(models.Model):
	"""A custom data-collection form created by a verified doctor for a specific patient."""

	META_ENTRY_TIME = 'entry_time'
	META_ENTRY_DAY = 'entry_day'
	META_PATIENT_REGION = 'patient_region'
	META_PATIENT_GENDER = 'patient_gender'
	META_DEVICE_TYPE = 'device_type'
	META_IP_APPROX_LOCATION = 'ip_approx_location'
	META_SESSION_SOURCE = 'session_source'
	META_CHOICES = [
		(META_ENTRY_TIME, 'Muda wa kujaza (timestamp)'),
		(META_ENTRY_DAY, 'Siku ya wiki'),
		(META_PATIENT_REGION, 'Location/Region ya patient'),
		(META_PATIENT_GENDER, 'Gender ya patient'),
		(META_DEVICE_TYPE, 'Aina ya kifaa (device type)'),
		(META_IP_APPROX_LOCATION, 'IP-based approximate location'),
		(META_SESSION_SOURCE, 'Session source (web/app/referrer)'),
	]

	doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_patient_logs')
	patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_patient_logs')
	title = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	frequency = models.CharField(
		max_length=120, blank=True,
		help_text='Mfano: Mara 2 kwa siku, Kila asubuhi baada ya chakula',
	)
	is_active = models.BooleanField(default=True)
	is_sent = models.BooleanField(default=False, help_text='Imekuwa sent kwa patient au bado')
	metadata_fields = models.JSONField(
		default=list,
		blank=True,
		help_text='Metadata zilizoruhusiwa na daktari kwa analysis, mfano ["entry_time","patient_region"]',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Log '{self.title}' (Dr.{self.doctor.username} → {self.patient.username})"

	def entry_count(self):
		return self.entries.count()


class PatientLogField(models.Model):
	FIELD_TEXT = 'text'
	FIELD_TEXTAREA = 'textarea'
	FIELD_NUMBER = 'number'
	FIELD_SELECT = 'select'
	FIELD_CHECKBOX = 'checkbox'
	FIELD_SCALE = 'scale'

	FIELD_TYPE_CHOICES = [
		(FIELD_TEXT, 'Maandishi mafupi'),
		(FIELD_TEXTAREA, 'Maandishi marefu'),
		(FIELD_NUMBER, 'Namba'),
		(FIELD_SELECT, 'Chaguo (dropdown)'),
		(FIELD_CHECKBOX, 'Ndio/Hapana'),
		(FIELD_SCALE, 'Kiwango 1–10'),
	]

	log = models.ForeignKey(PatientLog, on_delete=models.CASCADE, related_name='fields')
	field_label = models.CharField(max_length=200)
	field_type = models.CharField(max_length=20, choices=FIELD_TYPE_CHOICES, default=FIELD_TEXT)
	placeholder = models.CharField(max_length=250, blank=True)
	options = models.JSONField(default=list, blank=True, help_text='Kwa select: orodha ya chaguzi, kwa mfano ["Ndiyo","Hapana"]')
	required = models.BooleanField(default=False)
	order = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['order', 'id']

	def __str__(self):
		return f"{self.field_label} ({self.field_type})"


class PatientLogEntry(models.Model):
	"""A single submission from a patient filling in their assigned log."""

	log = models.ForeignKey(PatientLog, on_delete=models.CASCADE, related_name='entries')
	submitted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='log_entries')
	data = models.JSONField(default=dict)
	metadata = models.JSONField(default=dict, blank=True)
	submitted_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-submitted_at']

	def __str__(self):
		return f"Entry by {self.submitted_by.username} — {self.log.title} @ {self.submitted_at:%Y-%m-%d %H:%M}"
