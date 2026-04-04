from django.conf import settings
from django.db import models
from django.utils import timezone


class UserAIPersona(models.Model):
	GENDER_CHOICES = [
		('female', 'Female'),
		('male', 'Male'),
		('other', 'Other'),
		('prefer_not', 'Prefer not to say'),
	]
	STRESS_CHOICES = [
		('low', 'Low'),
		('moderate', 'Moderate'),
		('high', 'High'),
	]
	EXERCISE_CHOICES = [
		('none', 'No regular exercise'),
		('light', 'Light 1-2x/week'),
		('moderate', 'Moderate 3-4x/week'),
		('high', 'High 5x+/week'),
	]

	user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ai_persona')

	# Step 1: Basic info (Required)
	age = models.PositiveSmallIntegerField(null=True, blank=True)
	birth_date = models.DateField(null=True, blank=True)
	gender = models.CharField(max_length=20, choices=GENDER_CHOICES, blank=True)
	height_cm = models.PositiveSmallIntegerField(null=True, blank=True)
	weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

	# Step 2: Health info (Required)
	health_notes = models.TextField(blank=True, help_text='General health information')
	permanent_diseases = models.TextField(blank=True)
	medications = models.TextField(blank=True)

	# Step 3: Lifestyle (Required + Optional)
	lifestyle_notes = models.TextField(blank=True)
	sleep_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
	stress_level = models.CharField(max_length=20, choices=STRESS_CHOICES, blank=True)
	exercise_frequency = models.CharField(max_length=20, choices=EXERCISE_CHOICES, blank=True)

	# Optional
	diet = models.TextField(blank=True)
	goals = models.TextField(blank=True)
	mental_health = models.TextField(blank=True)
	emergency_contact_name = models.CharField(max_length=120, blank=True)
	emergency_contact_phone = models.CharField(max_length=30, blank=True)
	location_region = models.CharField(max_length=120, blank=True)
	language_preference = models.CharField(max_length=30, default='sw')
	ai_data_consent = models.BooleanField(default=True)
	identity_verified = models.BooleanField(default=False)
	medical_info_verified = models.BooleanField(default=False)
	verification_notes = models.TextField(blank=True)
	last_data_reviewed_at = models.DateTimeField(null=True, blank=True)
	profile_completeness_score = models.PositiveSmallIntegerField(default=0)

	# Profile
	avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
	bio = models.TextField(blank=True, max_length=300)

	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"AI Persona - {self.user}"

	def _calculate_age_from_birth_date(self):
		if not self.birth_date:
			return None
		today = timezone.localdate()
		years = today.year - self.birth_date.year
		if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
			years -= 1
		return max(years, 0)

	def save(self, *args, **kwargs):
		calculated_age = self._calculate_age_from_birth_date()
		if calculated_age is not None:
			self.age = calculated_age
		super().save(*args, **kwargs)

	def calculate_completeness_score(self):
		tracked_fields = {
			'birth_date': self.birth_date,
			'age': self.age,
			'gender': self.gender,
			'height_cm': self.height_cm,
			'weight_kg': self.weight_kg,
			'health_notes': self.health_notes.strip(),
			'permanent_diseases': self.permanent_diseases.strip(),
			'medications': self.medications.strip(),
			'lifestyle_notes': self.lifestyle_notes.strip(),
			'sleep_hours': self.sleep_hours,
			'stress_level': self.stress_level,
			'exercise_frequency': self.exercise_frequency,
			'diet': self.diet.strip(),
			'goals': self.goals.strip(),
			'mental_health': self.mental_health.strip(),
			'emergency_contact_name': self.emergency_contact_name.strip(),
			'emergency_contact_phone': self.emergency_contact_phone.strip(),
			'location_region': self.location_region.strip(),
			'language_preference': self.language_preference,
		}
		total = len(tracked_fields)
		filled = sum(1 for value in tracked_fields.values() if bool(value))
		return round((filled / total) * 100) if total else 0

	def update_quality_metrics(self, save=True):
		self.profile_completeness_score = self.calculate_completeness_score()
		self.last_data_reviewed_at = timezone.now()
		if save:
			self.save(update_fields=['profile_completeness_score', 'last_data_reviewed_at', 'updated_at'])

	@property
	def data_quality_label(self):
		score = self.profile_completeness_score or 0
		if score >= 85:
			return 'high'
		if score >= 60:
			return 'medium'
		return 'low'

	@property
	def onboarding_complete(self):
		required = [
			self.birth_date,
			self.gender,
		]
		return all(bool(v) for v in required)


class PersonaDataSnapshot(models.Model):
	SOURCE_CHOICES = [
		('onboarding', 'Onboarding'),
		('profile_update', 'Profile update'),
		('periodic', 'Periodic capture'),
	]

	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='persona_snapshots')
	persona = models.ForeignKey(UserAIPersona, on_delete=models.CASCADE, related_name='snapshots')
	source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='profile_update')
	completeness_score = models.PositiveSmallIntegerField(default=0)
	identity_verified = models.BooleanField(default=False)
	medical_info_verified = models.BooleanField(default=False)
	payload = models.JSONField(default=dict)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Snapshot({self.user}) {self.created_at:%Y-%m-%d %H:%M}"
