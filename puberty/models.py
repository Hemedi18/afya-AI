from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class PubertyProfile(models.Model):
	GENDER_CHOICES = [
		("male", "Male"),
		("female", "Female"),
		("other", "Other"),
	]
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="puberty_profile")
	gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
	age = models.PositiveIntegerField()
	puberty_stage = models.CharField(max_length=50)
	concerns = models.JSONField(default=dict, blank=True)
	country = models.CharField(max_length=64)
	created_at = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"{self.user.username} ({self.gender}, {self.age})"

class PubertyQuestion(models.Model):
	CATEGORY_CHOICES = [
		("general", "General"),
		("mental_health", "Mental Health"),
		("hygiene", "Hygiene"),
		("menstrual", "Menstrual"),
		("body_change", "Body Change"),
		("voice_change", "Voice Change"),
		("emotional", "Emotional"),
		("cultural", "Cultural"),
	]
	question = models.TextField()
	category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
	gender_specific = models.CharField(max_length=10, choices=PubertyProfile.GENDER_CHOICES, blank=True, null=True)
	age_group = models.CharField(max_length=32, blank=True, null=True)

	def __str__(self):
		return self.question[:60]

class PubertyAnswer(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	question = models.ForeignKey(PubertyQuestion, on_delete=models.CASCADE)
	answer = models.TextField()
	created_at = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"{self.user.username} - {self.question.id}"

class PubertyGuide(models.Model):
	GENDER_CHOICES = PubertyProfile.GENDER_CHOICES
	title = models.CharField(max_length=128)
	description = models.TextField()
	gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True, null=True)
	age_group = models.CharField(max_length=32, blank=True, null=True)
	content = models.TextField()
	image = models.ImageField(upload_to="puberty/guides/", blank=True, null=True)

	def __str__(self):
		return self.title

class PubertyTip(models.Model):
	CATEGORY_CHOICES = PubertyQuestion.CATEGORY_CHOICES
	title = models.CharField(max_length=128)
	content = models.TextField()
	category = models.CharField(max_length=32, choices=CATEGORY_CHOICES)
	priority = models.PositiveIntegerField(default=1)

	class Meta:
		ordering = ["priority", "title"]

	def __str__(self):
		return self.title
from django.conf import settings

