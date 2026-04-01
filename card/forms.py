from django import forms

from .models import HealthCard, PersonaReminderConfig


class HealthCardForm(forms.ModelForm):
    class Meta:
        model = HealthCard
        fields = [
            'full_name_override',
            'gender_override',
            'birth_date',
            'photo',
            'style_theme',
            'show_watermark',
            'watermark_text',
            'show_name',
            'show_gender',
            'show_birth_date',
            'show_age',
            'show_health_notes',
            'show_permanent_diseases',
            'show_medications',
            'show_goals',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'full_name_override': forms.TextInput(attrs={'placeholder': 'Acha wazi kutumia jina la profile'}),
            'gender_override': forms.TextInput(attrs={'placeholder': 'Acha wazi kutumia gender ya persona'}),
            'watermark_text': forms.TextInput(attrs={'placeholder': 'Mfano: afya-AI • VERIFIED'}),
        }


class PersonaReminderConfigForm(forms.ModelForm):
    class Meta:
        model = PersonaReminderConfig
        fields = ['interval_days', 'reminder_cooldown_days']
        widgets = {
            'interval_days': forms.NumberInput(attrs={'min': 7, 'max': 365}),
            'reminder_cooldown_days': forms.NumberInput(attrs={'min': 1, 'max': 60}),
        }

    def clean_interval_days(self):
        value = self.cleaned_data['interval_days']
        return min(max(value, 7), 365)

    def clean_reminder_cooldown_days(self):
        value = self.cleaned_data['reminder_cooldown_days']
        return min(max(value, 1), 60)
