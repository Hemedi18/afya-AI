import secrets
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class MobileAuthToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='mobile_tokens')
    key = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-last_used_at']

    def __str__(self):
        return f"{self.user} token"

    @classmethod
    def issue_for_user(cls, user):
        cls.objects.filter(user=user, is_active=True).update(is_active=False)
        return cls.objects.create(
            user=user,
            key=secrets.token_hex(32),
            expires_at=timezone.now() + timedelta(days=30),
        )

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def touch(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])
