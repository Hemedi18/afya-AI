from django.conf import settings
from django.db import models


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

	# Profile
	avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
	bio = models.TextField(blank=True, max_length=300)

	updated_at = models.DateTimeField(auto_now=True)

	def __str__(self):
		return f"AI Persona - {self.user}"

	@property
	def onboarding_complete(self):
		required = [
			self.age,
			self.gender,
			self.height_cm,
			self.weight_kg,
			self.health_notes.strip(),
			self.permanent_diseases.strip(),
			self.medications.strip(),
			self.lifestyle_notes.strip(),
			self.sleep_hours,
			self.stress_level,
			self.exercise_frequency,
		]
		return all(bool(v) for v in required)
