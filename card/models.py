from datetime import timedelta
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from users.models import UserAIPersona


class CardNotification(models.Model):
	KIND_PERSONA_UPDATE = 'persona_update'
	KIND_CARD_UPDATED = 'card_updated'
	KIND_CHOICES = [
		(KIND_PERSONA_UPDATE, 'Persona Update Reminder'),
		(KIND_CARD_UPDATED, 'Card Updated'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='card_notifications')
	kind = models.CharField(max_length=40, choices=KIND_CHOICES)
	title = models.CharField(max_length=150)
	body = models.TextField(blank=True)
	is_read = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.user} - {self.title}"


class PersonaReminderConfig(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='persona_reminder_config')
	interval_days = models.PositiveSmallIntegerField(default=30)
	reminder_cooldown_days = models.PositiveSmallIntegerField(default=7)
	last_notified_at = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"Reminder config - {self.user}"


class HealthCard(models.Model):
	STYLE_CLASSIC = 'classic'
	STYLE_AURORA = 'aurora'
	STYLE_MIDNIGHT = 'midnight'
	STYLE_EMERALD = 'emerald'
	STYLE_CHOICES = [
		(STYLE_CLASSIC, 'Classic'),
		(STYLE_AURORA, 'Aurora'),
		(STYLE_MIDNIGHT, 'Midnight'),
		(STYLE_EMERALD, 'Emerald'),
	]

	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='health_card')
	public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

	# Front data defaults (can be overridden)
	full_name_override = models.CharField(max_length=150, blank=True)
	gender_override = models.CharField(max_length=30, blank=True)
	birth_date = models.DateField(null=True, blank=True)
	photo = models.ImageField(upload_to='health_cards/photos/', null=True, blank=True)
	style_theme = models.CharField(max_length=20, choices=STYLE_CHOICES, default=STYLE_CLASSIC)
	watermark_text = models.CharField(max_length=80, blank=True, default='afya-AI')
	show_watermark = models.BooleanField(default=True)

	# Selective visibility for scan payload
	show_name = models.BooleanField(default=True)
	show_gender = models.BooleanField(default=True)
	show_birth_date = models.BooleanField(default=True)
	show_age = models.BooleanField(default=True)
	show_health_notes = models.BooleanField(default=False)
	show_permanent_diseases = models.BooleanField(default=False)
	show_medications = models.BooleanField(default=False)
	show_goals = models.BooleanField(default=False)
	show_menstrual_logs = models.BooleanField(default=False)
	show_menstrual_chart = models.BooleanField(default=False)
	show_ai_summary = models.BooleanField(default=False)
	show_lifestyle = models.BooleanField(default=False)

	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"HealthCard - {self.user}"

	@property
	def display_name(self):
		if self.full_name_override.strip():
			return self.full_name_override.strip()
		return self.user.get_full_name() or self.user.username

	@property
	def display_gender(self):
		if self.gender_override.strip():
			return self.gender_override.strip()
		persona = getattr(self.user, 'ai_persona', None)
		return (persona.gender if persona and persona.gender else 'Not set').title()

	@property
	def display_birth_date(self):
		return self.birth_date

	@property
	def display_age(self):
		if not self.birth_date:
			return None
		today = timezone.localdate()
		years = today.year - self.birth_date.year
		if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
			years -= 1
		return max(years, 0)

	@property
	def display_photo_url(self):
		if self.photo:
			return self.photo.url
		persona = getattr(self.user, 'ai_persona', None)
		if persona and persona.avatar:
			return persona.avatar.url
		return None

	def build_public_payload(self):
		persona = UserAIPersona.objects.filter(user=self.user).first()
		payload = {
			'username': self.user.username,
			'updated_at': self.updated_at.isoformat(),
		}
		if self.show_name:
			payload['full_name'] = self.display_name
		if self.show_gender:
			payload['gender'] = self.display_gender
		if self.show_birth_date and self.birth_date:
			payload['birth_date'] = self.birth_date.isoformat()
		if self.show_age and self.display_age is not None:
			payload['age'] = self.display_age

		if persona:
			if self.show_health_notes and persona.health_notes.strip():
				payload['health_notes'] = persona.health_notes
			if self.show_permanent_diseases and persona.permanent_diseases.strip():
				payload['permanent_diseases'] = persona.permanent_diseases
			if self.show_medications and persona.medications.strip():
				payload['medications'] = persona.medications
			if self.show_goals and persona.goals.strip():
				payload['goals'] = persona.goals
			if self.show_lifestyle and persona.lifestyle_notes.strip():
				payload['lifestyle_notes'] = persona.lifestyle_notes
		return payload


def ensure_persona_update_notification(user):
	if not user.is_authenticated:
		return

	persona = UserAIPersona.objects.filter(user=user).first()
	if not persona:
		return

	config, _ = PersonaReminderConfig.objects.get_or_create(user=user)
	now = timezone.now()
	due_at = persona.updated_at + timedelta(days=config.interval_days)
	if now < due_at:
		return

	if config.last_notified_at:
		next_allowed = config.last_notified_at + timedelta(days=config.reminder_cooldown_days)
		if now < next_allowed:
			return

	CardNotification.objects.create(
		user=user,
		kind=CardNotification.KIND_PERSONA_UPDATE,
		title='Wakati wa kusasisha AI Persona',
		body='Data zako za persona zimepitwa na muda. Sasisha ili card na ushauri wa AI ubaki sahihi.',
	)
	config.last_notified_at = now
	config.save(update_fields=['last_notified_at', 'updated_at'])
