from django.db import models
from django.conf import settings

from menstrual.models import CommunityPost


User = settings.AUTH_USER_MODEL


class PubertyCheckRecord(models.Model):
	GENDER_CHOICES = [
		('female', 'Female'),
		('male', 'Male'),
		('other', 'Other'),
	]

	RISK_LOW = 'low'
	RISK_MEDIUM = 'medium'
	RISK_HIGH = 'high'
	RISK_CHOICES = [
		(RISK_LOW, 'Low'),
		(RISK_MEDIUM, 'Medium'),
		(RISK_HIGH, 'High'),
	]

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='puberty_checks')
	age = models.PositiveSmallIntegerField()
	gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='other')
	symptoms = models.JSONField(default=list, blank=True)
	severity = models.PositiveSmallIntegerField(default=1)
	notes = models.TextField(blank=True)
	risk_level = models.CharField(max_length=10, choices=RISK_CHOICES, default=RISK_LOW)
	red_flags = models.JSONField(default=list, blank=True)
	ai_guidance = models.TextField(blank=True)
	needs_doctor = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Check {self.user} ({self.risk_level})"


class PubertyHabitGoal(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='puberty_goals')
	title = models.CharField(max_length=180)
	details = models.TextField(blank=True)
	target_days = models.PositiveSmallIntegerField(default=21)
	streak_days = models.PositiveSmallIntegerField(default=0)
	completed_today = models.BooleanField(default=False)
	updated_at = models.DateTimeField(auto_now=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-updated_at']

	def __str__(self):
		return f"{self.title} ({self.user})"


class PubertyFinding(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='puberty_findings')
	title = models.CharField(max_length=180)
	finding = models.TextField()
	tags = models.CharField(max_length=200, blank=True, help_text='Comma separated tags')
	is_anonymous = models.BooleanField(default=False)
	share_to_community = models.BooleanField(default=False)
	community_post = models.ForeignKey(
		CommunityPost,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='puberty_findings',
	)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"Finding {self.title} by {self.user}"


class PubertyPreventionPlanDay(models.Model):
	check_record = models.ForeignKey(PubertyCheckRecord, on_delete=models.CASCADE, related_name='prevention_plan_days')
	day_number = models.PositiveSmallIntegerField()
	title = models.CharField(max_length=120)
	action = models.TextField()
	is_done = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['day_number']
		unique_together = ('check_record', 'day_number')

	def __str__(self):
		return f"Plan day {self.day_number} for check {self.check_record_id}"


class ReproductiveMetricEntry(models.Model):
	CATEGORY_PERFORMANCE = 'performance'
	CATEGORY_FERTILITY = 'fertility'
	CATEGORY_HORMONE = 'hormone'
	CATEGORY_MENTAL = 'mental'
	CATEGORY_URINARY = 'urinary'
	CATEGORY_CHOICES = [
		(CATEGORY_PERFORMANCE, 'Sexual Performance'),
		(CATEGORY_FERTILITY, 'Fertility'),
		(CATEGORY_HORMONE, 'Hormones'),
		(CATEGORY_MENTAL, 'Mental & Habits'),
		(CATEGORY_URINARY, 'Urinary/Reproductive General'),
	]

	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reproductive_metrics')
	category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
	metric_key = models.CharField(max_length=100)
	metric_value = models.FloatField(default=0)
	notes = models.TextField(blank=True)
	recorded_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-recorded_at']

	def __str__(self):
		return f"{self.user} {self.category}:{self.metric_key}={self.metric_value}"


class AIScoreSnapshot(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_score_snapshots')
	overall_score = models.PositiveSmallIntegerField(default=50)
	fertility_score = models.PositiveSmallIntegerField(default=50)
	sexual_performance_score = models.PositiveSmallIntegerField(default=50)
	hormone_balance_score = models.PositiveSmallIntegerField(default=50)
	stress_libido_score = models.PositiveSmallIntegerField(default=50)
	summary = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"AI Score {self.user} ({self.overall_score})"


class CoupleConnection(models.Model):
	STATUS_PENDING = 'pending'
	STATUS_ACCEPTED = 'accepted'
	STATUS_REJECTED = 'rejected'
	STATUS_CHOICES = [
		(STATUS_PENDING, 'Pending'),
		(STATUS_ACCEPTED, 'Accepted'),
		(STATUS_REJECTED, 'Rejected'),
	]

	requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='couple_requests_sent')
	partner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='couple_requests_received')
	status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-updated_at']
		unique_together = ('requester', 'partner')

	def __str__(self):
		return f"{self.requester} -> {self.partner} ({self.status})"

