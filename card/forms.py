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
            'show_lifestyle',
            'show_menstrual_logs',
            'show_menstrual_chart',
            'show_ai_summary',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'full_name_override': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Acha wazi kutumia jina la profile'}),
            'gender_override': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Acha wazi kutumia gender ya persona'}),
            'watermark_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mfano: afya-AI • VERIFIED'}),
            'style_theme': forms.Select(attrs={'class': 'form-select'}),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'show_watermark': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_name': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_gender': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_birth_date': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_age': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_health_notes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_permanent_diseases': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_medications': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_goals': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_lifestyle': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_menstrual_logs': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_menstrual_chart': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'show_ai_summary': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PersonaReminderConfigForm(forms.ModelForm):
    class Meta:
        model = PersonaReminderConfig
        fields = ['interval_days', 'reminder_cooldown_days']
        widgets = {
            'interval_days': forms.NumberInput(attrs={'min': 7, 'max': 365, 'class': 'form-control'}),
            'reminder_cooldown_days': forms.NumberInput(attrs={'min': 1, 'max': 60, 'class': 'form-control'}),
        }

    def clean_interval_days(self):
        value = self.cleaned_data['interval_days']
        return min(max(value, 7), 365)

    def clean_reminder_cooldown_days(self):
        value = self.cleaned_data['reminder_cooldown_days']
        return min(max(value, 1), 60)
