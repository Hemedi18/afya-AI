from django.db import models
from django.contrib.auth.models import User


class OfflineConversation(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offline_conversations')
	title = models.CharField(max_length=160, blank=True)
	model_name = models.CharField(max_length=80, default='llama3.2:3b')
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']

	def __str__(self):
		return self.title or f'Offline chat #{self.pk}'


class OfflineMessage(models.Model):
	ROLE_USER = 'user'
	ROLE_ASSISTANT = 'assistant'
	ROLE_SYSTEM = 'system'
	ROLE_CHOICES = [
		(ROLE_USER, 'User'),
		(ROLE_ASSISTANT, 'Assistant'),
		(ROLE_SYSTEM, 'System'),
	]

	conversation = models.ForeignKey(OfflineConversation, on_delete=models.CASCADE, related_name='messages')
	role = models.CharField(max_length=10, choices=ROLE_CHOICES)
	content = models.TextField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['created_at']

	def __str__(self):
		return f'{self.role}: {self.content[:42]}'


class SmsWebhookLog(models.Model):
	sender = models.CharField(max_length=40, blank=True)
	message_text = models.TextField(blank=True)
	reply_text = models.TextField(blank=True)
	outbound_sent = models.BooleanField(default=False)
	outbound_detail = models.TextField(blank=True)
	raw_payload = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f'{self.sender or "unknown"} @ {self.created_at:%Y-%m-%d %H:%M:%S}'

# Create your models here.
