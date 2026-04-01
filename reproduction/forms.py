from django import forms

from .models import PubertyCheckRecord, PubertyFinding, PubertyHabitGoal, ReproductiveMetricEntry


SYMPTOM_CHOICES = [
    ('irregular_periods', 'Irregular periods / kuchelewa hedhi'),
    ('severe_cramps', 'Severe cramps / maumivu makali ya tumbo'),
    ('heavy_bleeding', 'Heavy bleeding / damu nyingi hedhini'),
    ('unusual_discharge', 'Unusual vaginal/penile discharge'),
    ('itching_burning', 'Itching or burning in private parts'),
    ('painful_urination', 'Painful urination'),
    ('genital_sores', 'Genital sores or wounds'),
    ('testicular_pain', 'Testicular pain/swelling'),
    ('erection_issues', 'Erection issues / low libido'),
    ('breast_lump', 'Breast lump or persistent pain'),
    ('early_puberty_signs', 'Very early puberty signs'),
    ('delayed_puberty_signs', 'Delayed puberty signs'),
    ('strong_body_odor', 'Strong body odor + acne + mood swings'),
]


class PubertyCheckForm(forms.ModelForm):
    symptoms = forms.MultipleChoiceField(
        choices=SYMPTOM_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = PubertyCheckRecord
        fields = ['age', 'gender', 'symptoms', 'severity', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Andika maelezo ya ziada...'}),
            'severity': forms.NumberInput(attrs={'min': 1, 'max': 5}),
        }


class PubertyHabitGoalForm(forms.ModelForm):
    class Meta:
        model = PubertyHabitGoal
        fields = ['title', 'details', 'target_days']
        widgets = {
            'details': forms.Textarea(attrs={'rows': 3}),
            'target_days': forms.NumberInput(attrs={'min': 7, 'max': 180}),
        }


class PubertyFindingForm(forms.ModelForm):
    class Meta:
        model = PubertyFinding
        fields = ['title', 'finding', 'tags', 'is_anonymous', 'share_to_community']
        widgets = {
            'finding': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Umegundua nini kuhusu afya ya uzazi?'}),
            'tags': forms.TextInput(attrs={'placeholder': 'mfano: period, hygiene, stress'}),
        }


class ReproductiveMetricEntryForm(forms.ModelForm):
    class Meta:
        model = ReproductiveMetricEntry
        fields = ['category', 'metric_key', 'metric_value', 'notes']
        widgets = {
            'metric_key': forms.TextInput(attrs={'placeholder': 'mfano: libido, erection_quality, ovulation_pain'}),
            'metric_value': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'max': '100'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional notes...'}),
        }


class CoupleConnectForm(forms.Form):
    partner_username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'placeholder': 'Username wa partner'}))
