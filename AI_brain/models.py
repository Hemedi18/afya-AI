from django.conf import settings
from django.db import models


class AIInteractionLog(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_interactions')
	question = models.TextField()
	reply = models.TextField(blank=True)
	persona_completeness = models.PositiveSmallIntegerField(default=0)
	identity_verified = models.BooleanField(default=False)
	medical_info_verified = models.BooleanField(default=False)
	context_payload = models.JSONField(default=dict)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"AI chat: {self.user} @ {self.created_at:%Y-%m-%d %H:%M}"
