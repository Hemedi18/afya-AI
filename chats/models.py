from django.conf import settings
from django.db import models

from menstrual.models import CommunityPost, CommunityReply


User = settings.AUTH_USER_MODEL


class PrivateConversation(models.Model):
	patient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_conversations')
	doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='doctor_conversations')
	subject = models.CharField(max_length=180)
	is_closed = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']

	def __str__(self):
		return f"{self.patient} ↔ {self.doctor}"


class PrivateMessage(models.Model):
	conversation = models.ForeignKey(PrivateConversation, on_delete=models.CASCADE, related_name='messages')
	sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='private_messages_sent')
	content = models.TextField()
	attachment = models.FileField(upload_to='private_chat_attachments/', blank=True, null=True)
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f"Message by {self.sender} at {self.created_at}"


class ContentReport(models.Model):
	STATUS_OPEN = 'open'
	STATUS_REVIEWING = 'reviewing'
	STATUS_RESOLVED = 'resolved'
	STATUS_CHOICES = [
		(STATUS_OPEN, 'Open'),
		(STATUS_REVIEWING, 'Reviewing'),
		(STATUS_RESOLVED, 'Resolved'),
	]

	reporter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='content_reports')
	post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
	comment = models.ForeignKey(CommunityReply, on_delete=models.CASCADE, null=True, blank=True, related_name='reports')
	reason = models.CharField(max_length=200)
	details = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
	created_at = models.DateTimeField(auto_now_add=True)
	reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_reports')

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		target = self.post_id or self.comment_id
		return f"Report {target} by {self.reporter}"


class ClarificationRequest(models.Model):
	TARGET_ADMIN = 'admin'
	TARGET_DOCTOR = 'doctor'
	TARGET_CHOICES = [
		(TARGET_ADMIN, 'Admin'),
		(TARGET_DOCTOR, 'Doctor'),
	]

	STATUS_OPEN = 'open'
	STATUS_ANSWERED = 'answered'
	STATUS_CHOICES = [
		(STATUS_OPEN, 'Open'),
		(STATUS_ANSWERED, 'Answered'),
	]

	asker = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clarification_requests')
	post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, null=True, blank=True, related_name='clarifications')
	comment = models.ForeignKey(CommunityReply, on_delete=models.CASCADE, null=True, blank=True, related_name='clarifications')
	target_role = models.CharField(max_length=20, choices=TARGET_CHOICES, default=TARGET_DOCTOR)
	target_doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='clarification_targets')
	question = models.TextField()
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
	response = models.TextField(blank=True)
	responded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='clarifications_answered')
	likes = models.ManyToManyField(User, related_name='clarification_likes', blank=True)
	dislikes = models.ManyToManyField(User, related_name='clarification_dislikes', blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		target = f"post:{self.post_id}" if self.post_id else f"comment:{self.comment_id}"
		return f"Clarification {target} by {self.asker}"


class ClarificationMessage(models.Model):
	clarification = models.ForeignKey(ClarificationRequest, on_delete=models.CASCADE, related_name='messages')
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='clarification_messages')
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f"Clarification message {self.clarification_id} by {self.user}"
