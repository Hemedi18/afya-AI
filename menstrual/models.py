from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_q.tasks import async_task

User = settings.AUTH_USER_MODEL


def default_status_expiry():
    return timezone.now() + timezone.timedelta(hours=24)

# 1. CYCLE TRACKING
class MenstrualCycle(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cycles')
    start_date = models.DateField(verbose_name=_("Start Date"), help_text=_("Siku ya kwanza ya kuanza mzunguko"))
    expected_end_date = models.DateField(verbose_name=_("Expected End Date"), help_text=_("Siku inayotarajiwa kuisha"))
    cycle_length = models.PositiveSmallIntegerField(default=28, help_text=_("Urefu wa mzunguko (siku), mfano 28"))
    period_duration = models.PositiveSmallIntegerField(default=5, help_text=_("Muda wa hedhi kwa siku, mfano 5"))
    is_active = models.BooleanField(default=True)
    
    @property
    def elapsed_days(self):
        if self.is_active:
            # Return +1 so the start date is accurately represented as 'Day 1'
            return (timezone.now().date() - self.start_date).days + 1
        return 0

    def __str__(self):
        return f"{self.user.username} - {self.start_date}"

# 2. DAILY LOGGING (Custom Inputs using JSONField)
class DailyLog(models.Model):
    cycle = models.ForeignKey(MenstrualCycle, on_delete=models.CASCADE, related_name='daily_logs')
    date = models.DateField(default=timezone.now)
    
    # Flow Intensity (1 to 5 drops)
    flow_intensity = models.IntegerField(default=0, help_text=_("Weka kiwango cha damu (1-5)"))
    flow_notes = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Flow Notes"))
    
    # Custom choices & user-entered data stored in JSON
    physical_symptoms = models.JSONField(default=list, help_text=_("Cramps, bloating, headaches, etc."))
    emotional_changes = models.JSONField(default=list, help_text=_("Mood swings, anxiety, etc."))
    sleep_patterns = models.JSONField(default=list, help_text=_("Trouble sleeping or tired"))
    
    # AI Logic update field
    ai_suggestion = models.TextField(blank=True, null=True, verbose_name=_("AI Suggestions"))

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        # Trigger AI insights if this is a new log with data
        has_data = (
            self.flow_intensity > 0 or 
            self.physical_symptoms or self.emotional_changes or self.sleep_patterns
        )
        if is_new and has_data:
            # Ensure the task is only queued after the DB transaction is committed
            transaction.on_commit(
                lambda: async_task('menstrual.tasks.generate_log_insight_task', self.id))

    class Meta:
        unique_together = ('cycle', 'date')
        
    def __str__(self):
        return f"Log for {self.date} - User: {self.cycle.user.username}"

# 3. DAILY TIPS & AI WEB SEARCH
class DailyTip(models.Model):
    SOURCE_CHOICES = (
        ('AI', _('Artificial Intelligence')),
        ('DOCTOR', _('Professional Doctor')),
        ('WEB', _('Verified Website')),
    )
    title = models.CharField(max_length=200, verbose_name=_("Tip Header"))
    content = models.TextField(verbose_name=_("Tip Content"))
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default='AI')
    url = models.URLField(blank=True, null=True, help_text=_("Source URL link"))
    
    # AI generates background colors/styles here
    ui_structure = models.JSONField(default=dict, help_text=_("AI generated CSS/Visual structure"))
    
    date_created = models.DateField(auto_now_add=True)
    saved_permanent = models.ManyToManyField(User, related_name='permanent_tips', blank=True)

    def __str__(self):
        return self.title

# 4. COMMUNITY CHATTING (Social Section)
class CommunityPost(models.Model):
    AUDIENCE_FEMALE = 'female'
    AUDIENCE_MALE = 'male'
    AUDIENCE_CHOICES = [
        (AUDIENCE_FEMALE, _('Female community')),
        (AUDIENCE_MALE, _('Male community')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey('CommunityGroup', on_delete=models.SET_NULL, null=True, blank=True, related_name='posts')
    groups = models.ManyToManyField('CommunityGroup', blank=True, related_name='multi_posts')
    content = models.TextField(verbose_name=_("What's on your mind?"))
    image = models.ImageField(upload_to='community_posts/', blank=True, null=True)
    video = models.FileField(upload_to='community_posts/videos/', blank=True, null=True)
    media_ratio = models.CharField(max_length=20, default='auto')
    media_shape = models.CharField(max_length=20, default='rounded')
    media_focus_x = models.PositiveSmallIntegerField(default=50)
    media_focus_y = models.PositiveSmallIntegerField(default=50)
    is_anonymous = models.BooleanField(default=False)
    audience_gender = models.CharField(max_length=10, choices=AUDIENCE_CHOICES, default=AUDIENCE_FEMALE)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name='post_likes', blank=True)

    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"

    def display_groups(self):
        selected_groups = list(self.groups.all())
        if selected_groups:
            return selected_groups
        if self.group_id:
            return [self.group]
        return []

    @property
    def has_media(self):
        return bool(self.image or self.video)

class CommunityReply(models.Model):
    post = models.ForeignKey(CommunityPost, on_delete=models.CASCADE, related_name='replies')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='child_replies')
    content = models.TextField()
    likes = models.ManyToManyField(User, related_name='comment_likes', blank=True)
    dislikes = models.ManyToManyField(User, related_name='comment_dislikes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class CommunityGroup(models.Model):
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    audience_gender = models.CharField(max_length=10, choices=CommunityPost.AUDIENCE_CHOICES, default=CommunityPost.AUDIENCE_FEMALE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_community_groups')
    members = models.ManyToManyField(User, related_name='community_groups', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        unique_together = ('name', 'audience_gender')

    def __str__(self):
        return f"{self.name} ({self.audience_gender})"


class CommunityStatus(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_statuses')
    group = models.ForeignKey(CommunityGroup, on_delete=models.SET_NULL, null=True, blank=True, related_name='statuses')
    audience_gender = models.CharField(max_length=10, choices=CommunityPost.AUDIENCE_CHOICES, default=CommunityPost.AUDIENCE_FEMALE)
    content = models.CharField(max_length=250)
    image = models.ImageField(upload_to='community_status/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_status_expiry)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Status by {self.user}"

# 5. DOCTOR PROFILE & CONTACT
class DoctorProfile(models.Model):
    GENDER_CHOICES = [
        ('female', _('Female')),
        ('male', _('Male')),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='female')
    specialization = models.CharField(max_length=100)
    bio = models.TextField()
    hospital_name = models.CharField(max_length=200, blank=True)
    verified = models.BooleanField(default=False)

    def __str__(self):
        return f"Dr. {self.user.username}"

# 6. REMINDERS & NOTIFICATIONS
class Reminder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=200)
    event_date = models.DateField()
    reminder_time = models.TimeField(null=True, blank=True)
    is_notified = models.BooleanField(default=False)

    def __str__(self):
        return f"Reminder: {self.title} for {self.user.username}"


class MenstrualUserSetting(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='menstrual_settings')
    privacy_mode = models.BooleanField(default=True, help_text=_("Hide sensitive details on dashboard"))
    anonymous_mode = models.BooleanField(default=False, help_text=_("Post to community anonymously by default"))
    emergency_alerts_enabled = models.BooleanField(default=True)
    reminder_period = models.BooleanField(default=True)
    reminder_ovulation = models.BooleanField(default=True)
    reminder_fertile_window = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Menstrual settings - {self.user.username}"