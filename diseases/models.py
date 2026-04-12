from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Disease(models.Model):
    """Global Library of Diseases."""
    name = models.CharField(max_length=255, unique=True)
    icd_code = models.CharField(max_length=20, blank=True, null=True)
    definition = models.TextField()
    symptoms = models.TextField()
    prevention = models.TextField()
    treatment = models.TextField()
    body_system = models.CharField(max_length=100, blank=True)
    is_chronic = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return self.name

class UserDisease(models.Model):
    """User's personal disease profile."""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('controlled', 'Under Control'),
        ('recovered', 'Recovered'),
        ('monitoring', 'Monitoring'),
    ]
    SEVERITY_CHOICES = [(i, f'Level {i}') for i in range(1, 11)]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_diseases')
    disease_ref = models.ForeignKey(Disease, on_delete=models.SET_NULL, null=True, blank=True)
    custom_name = models.CharField(max_length=255, help_text="In case the disease isn't in our library")
    diagnosis_date = models.DateField(default=timezone.now)
    severity_level = models.IntegerField(choices=SEVERITY_CHOICES, default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_chronic = models.BooleanField(default=False)
    doctor_name = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)
    
    # AI Generated
    risk_score = models.IntegerField(default=0) 
    last_ai_insight = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.disease_ref.name if self.disease_ref else self.custom_name}"

class DiseaseLog(models.Model):
    """Daily tracking for a specific disease instance."""
    user_disease = models.ForeignKey(UserDisease, on_delete=models.CASCADE, related_name='logs')
    date = models.DateField(default=timezone.now)
    
    # Symptoms & Metrics
    symptoms_noted = models.TextField(help_text="Describe how you feel today")
    severity_score = models.IntegerField(default=1) # 1-10
    temperature = models.FloatField(null=True, blank=True)
    bp_systolic = models.IntegerField(null=True, blank=True)
    bp_diastolic = models.IntegerField(null=True, blank=True)
    oxygen_level = models.IntegerField(null=True, blank=True)
    blood_sugar = models.FloatField(null=True, blank=True)
    weight_kg = models.FloatField(null=True, blank=True)
    
    # Lifestyle
    mood = models.CharField(max_length=100, blank=True)
    energy_level = models.IntegerField(default=5) # 1-10
    sleep_hours = models.FloatField(default=8.0)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']
        unique_together = ['user_disease', 'date']

class DiseaseMedication(models.Model):
    """Medications linked to a specific disease."""
    user_disease = models.ForeignKey(UserDisease, on_delete=models.CASCADE, related_name='medications')
    name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100, help_text="e.g., Twice a day")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    side_effects = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} for {self.user_disease}"

class MedicationLog(models.Model):
    """Inatunza kumbukumbu ya kama dawa imemezwa kwa siku husika."""
    medication = models.ForeignKey(DiseaseMedication, on_delete=models.CASCADE, related_name='intake_logs')
    date = models.DateField(default=timezone.now)
    taken = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['medication', 'date']