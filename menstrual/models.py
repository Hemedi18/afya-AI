from django.db import models, transaction
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from importlib import import_module

django_q_async_task = None
if getattr(settings, 'DJANGO_Q_AVAILABLE', False):
    try:
        from django_q.tasks import async_task as django_q_async_task
    except Exception:
        django_q_async_task = None


def async_task(task_path, *args, **kwargs):
    """Queue a task with Django Q when enabled, otherwise run it inline."""
    if django_q_async_task is not None:
        return django_q_async_task(task_path, *args, **kwargs)

    if isinstance(task_path, str) and '.' in task_path:
        module_path, func_name = task_path.rsplit('.', 1)
        module = import_module(module_path)
        func = getattr(module, func_name)
        return func(*args, **kwargs)
    raise RuntimeError('Task path must be a dotted string when django-q is unavailable')

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
    image = models.ImageField(upload_to='community_groups/', blank=True, null=True)
    audience_gender = models.CharField(max_length=10, choices=CommunityPost.AUDIENCE_CHOICES, default=CommunityPost.AUDIENCE_FEMALE)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_community_groups')
    members = models.ManyToManyField(User, related_name='community_groups', blank=True)
    require_join_approval = models.BooleanField(default=False)
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
    likes = models.ManyToManyField(User, related_name='community_status_likes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_status_expiry)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Status by {self.user}"


class CommunityStatusComment(models.Model):
    status = models.ForeignKey(CommunityStatus, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_status_comments')
    content = models.CharField(max_length=400)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment by {self.user} on status {self.status_id}"


class CommunityStatusShare(models.Model):
    status = models.ForeignKey(CommunityStatus, on_delete=models.CASCADE, related_name='shares')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_status_shares')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('status', 'user')

    def __str__(self):
        return f"Share by {self.user} on status {self.status_id}"


class CommunityGroupJoinRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES = [
        (STATUS_PENDING, _('Pending')),
        (STATUS_APPROVED, _('Approved')),
        (STATUS_REJECTED, _('Rejected')),
    ]

    group = models.ForeignKey(CommunityGroup, on_delete=models.CASCADE, related_name='join_requests')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='community_group_join_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    message = models.CharField(max_length=220, blank=True)
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_group_join_requests')
    is_notified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('group', 'user')

    def __str__(self):
        return f"{self.user} -> {self.group} ({self.status})"

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
    THEME_DEFAULT = 'default'
    THEME_GOLD = 'gold'
    THEME_ROSE = 'rose'
    THEME_OCEAN = 'ocean'
    THEME_LAVENDER = 'lavender'

    COLOR_THEME_CHOICES = [
        (THEME_DEFAULT, _('Default Green')),
        (THEME_GOLD, _('Gold')),
        (THEME_ROSE, _('Rose')),
        (THEME_OCEAN, _('Ocean')),
        (THEME_LAVENDER, _('Lavender')),
    ]

    BG_SOLID = 'solid'
    BG_LINEAR = 'linear'
    BG_RADIAL = 'radial'
    BACKGROUND_STYLE_CHOICES = [
        (BG_SOLID, _('Solid')),
        (BG_LINEAR, _('Linear Gradient')),
        (BG_RADIAL, _('Radial Gradient')),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='menstrual_settings')
    privacy_mode = models.BooleanField(default=True, help_text=_("Hide sensitive details on dashboard"))
    anonymous_mode = models.BooleanField(default=False, help_text=_("Post to community anonymously by default"))
    emergency_alerts_enabled = models.BooleanField(default=True)
    reminder_period = models.BooleanField(default=True)
    reminder_ovulation = models.BooleanField(default=True)
    reminder_fertile_window = models.BooleanField(default=True)
    color_theme = models.CharField(max_length=20, choices=COLOR_THEME_CHOICES, default=THEME_DEFAULT)
    use_custom_palette = models.BooleanField(default=False)
    custom_primary = models.CharField(max_length=7, default='#2F6B3F')
    custom_secondary = models.CharField(max_length=7, default='#7FB77E')
    background_style = models.CharField(max_length=20, choices=BACKGROUND_STYLE_CHOICES, default=BG_LINEAR)
    background_intensity = models.PositiveSmallIntegerField(default=24)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Menstrual settings - {self.user.username}"