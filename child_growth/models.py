from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Child(models.Model):
	GENDER_CHOICES = [
		("male", "Male"),
		("female", "Female"),
		("other", "Other"),
	]
	BLOOD_GROUP_CHOICES = [
		("A+", "A+"), ("A-", "A-"), ("B+", "B+"), ("B-", "B-"),
		("AB+", "AB+"), ("AB-", "AB-"), ("O+", "O+"), ("O-", "O-")
	]
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="children")
	name = models.CharField(max_length=100)
	gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
	birth_date = models.DateField()
	birth_weight = models.FloatField(help_text="kg")
	birth_height = models.FloatField(help_text="cm")
	blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES, blank=True, null=True)
	created_at = models.DateTimeField(default=timezone.now)

	def __str__(self):
		return f"{self.name} ({self.user.username})"

class GrowthRecord(models.Model):
	child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="growth_records")
	weight = models.FloatField(help_text="kg")
	height = models.FloatField(help_text="cm")
	head_circumference = models.FloatField(help_text="cm", blank=True, null=True)
	recorded_at = models.DateField(default=timezone.now)

	def __str__(self):
		return f"{self.child.name} - {self.recorded_at}"

class DevelopmentMilestone(models.Model):
	title = models.CharField(max_length=128)
	age_range = models.CharField(max_length=32, help_text="e.g. 6-9 months")
	description = models.TextField()

	def __str__(self):
		return self.title

class ChildMilestone(models.Model):
	child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="milestones")
	milestone = models.ForeignKey(DevelopmentMilestone, on_delete=models.CASCADE)
	achieved = models.BooleanField(default=False)
	achieved_date = models.DateField(blank=True, null=True)

	def __str__(self):
		return f"{self.child.name} - {self.milestone.title}"

class NutritionTip(models.Model):
	title = models.CharField(max_length=128)
	description = models.TextField()
	age_group = models.CharField(max_length=32, help_text="e.g. 0-6 months, 6-12 months, 1-5 years")

	def __str__(self):
		return self.title

class Vaccination(models.Model):
	name = models.CharField(max_length=128)
	age_due = models.CharField(max_length=32, help_text="e.g. At birth, 6 weeks, 9 months")
	description = models.TextField()

	def __str__(self):
		return self.name

class ChildVaccination(models.Model):
	child = models.ForeignKey(Child, on_delete=models.CASCADE, related_name="vaccinations")
	vaccination = models.ForeignKey(Vaccination, on_delete=models.CASCADE)
	completed = models.BooleanField(default=False)
	completed_date = models.DateField(blank=True, null=True)

	def __str__(self):
		return f"{self.child.name} - {self.vaccination.name}"
from django.db import models

# Create your models here.
