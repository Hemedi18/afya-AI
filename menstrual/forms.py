from django import forms
import re
from datetime import timedelta
from .models import DailyLog, MenstrualCycle, MenstrualUserSetting, DailyTip

class MenstrualCycleForm(forms.ModelForm):
    class Meta:
        model = MenstrualCycle
        fields = ['start_date', 'cycle_length', 'period_duration', 'expected_end_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'cycle_length': forms.NumberInput(attrs={'class': 'form-control', 'min': 21, 'max': 45}),
            'period_duration': forms.NumberInput(attrs={'class': 'form-control', 'min': 2, 'max': 10}),
            'expected_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        expected_end_date = cleaned_data.get("expected_end_date")
        cycle_length = cleaned_data.get("cycle_length") or 28
        period_duration = cleaned_data.get("period_duration") or 5

        if cycle_length < 21 or cycle_length > 45:
            self.add_error('cycle_length', "Weka urefu wa mzunguko kati ya siku 21 hadi 45.")

        if period_duration < 2 or period_duration > 10:
            self.add_error('period_duration', "Weka muda wa hedhi kati ya siku 2 hadi 10.")

        if start_date and not expected_end_date:
            cleaned_data['expected_end_date'] = start_date + timedelta(days=period_duration - 1)
            expected_end_date = cleaned_data['expected_end_date']

        if start_date and expected_end_date and expected_end_date <= start_date:
            raise forms.ValidationError("Tarehe ya mwisho lazima iwe baada ya tarehe ya kuanza.")
        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['expected_end_date'].required = False

class DailyLogForm(forms.ModelForm):
    flow_intensity = forms.TypedChoiceField(
        choices=[(i, i) for i in range(1, 6)],
        coerce=int,
        required=True,
        widget=forms.RadioSelect,
    )

    physical_symptoms = forms.MultipleChoiceField(
        choices=[
            ('Cramps', 'Maumivu ya Tumbo (Cramps)'),
            ('Headache', 'Kuumwa Kichwa (Headache)'),
            ('Bloating', 'Tumbo Kujaa Gesi (Bloating)'),
            ('Fatigue', 'Uchovu (Fatigue)'),
            ('Acne', 'Chunusi (Acne)'),
            ('Nausea', 'Kichefuchefu (Nausea)'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple
    )

    emotional_changes = forms.MultipleChoiceField(
        choices=[
            ('Mood Swings', 'Mood swings'),
            ('Anxiety', 'Wasiwasi'),
            ('Low Mood', 'Hali ya chini'),
            ('Irritable', 'Kukasirika kirahisi'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    sleep_patterns = forms.MultipleChoiceField(
        choices=[
            ('Good Sleep', 'Nimelala vizuri'),
            ('Tired', 'Uchovu mwingi'),
            ('Insomnia', 'Usingizi mgumu'),
            ('Overslept', 'Kulala sana'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = DailyLog
        fields = [
            'date',
            'flow_intensity',
            'flow_notes',
            'physical_symptoms',
            'emotional_changes',
            'sleep_patterns',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'flow_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Andika maelezo ya leo...'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['date'].widget.attrs.update({'class': 'form-control'})
        self.fields['flow_intensity'].label = 'Kiwango cha Damu'
        self.fields['flow_notes'].label = 'Maelezo ya Ziada'
        self.fields['physical_symptoms'].label = 'Dalili za Mwili'
        self.fields['emotional_changes'].label = 'Mabadiliko ya Hisia'
        self.fields['sleep_patterns'].label = 'Usingizi na Uchovu'


class MenstrualUserSettingForm(forms.ModelForm):
    class Meta:
        model = MenstrualUserSetting
        fields = [
            'privacy_mode',
            'anonymous_mode',
            'emergency_alerts_enabled',
            'reminder_period',
            'reminder_ovulation',
            'reminder_fertile_window',
            'color_theme',
            'use_custom_palette',
            'custom_primary',
            'custom_secondary',
            'background_style',
            'background_intensity',
        ]
        widgets = {
            'privacy_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anonymous_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'emergency_alerts_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reminder_period': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reminder_ovulation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reminder_fertile_window': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'color_theme': forms.Select(attrs={'class': 'form-select'}),
            'use_custom_palette': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'custom_primary': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'custom_secondary': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'background_style': forms.Select(attrs={'class': 'form-select'}),
            'background_intensity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        }

    def clean_background_intensity(self):
        value = self.cleaned_data.get('background_intensity', 24)
        return min(max(value, 0), 100)

    def _validate_hex(self, value):
        if not value:
            return value
        if not re.fullmatch(r"#([0-9a-fA-F]{6})", value):
            raise forms.ValidationError('Tafadhali tumia hex color sahihi, mfano #D4AF37')
        return value

    def clean_custom_primary(self):
        return self._validate_hex(self.cleaned_data.get('custom_primary'))

    def clean_custom_secondary(self):
        return self._validate_hex(self.cleaned_data.get('custom_secondary'))


class DailyTipForm(forms.ModelForm):
    class Meta:
        model = DailyTip
        fields = ['title', 'content', 'url', 'source']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mfano: Kunywa maji zaidi wakati wa period'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Andika tip fupi, salama na ya kusaidia...'}),
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://example.com/source'}),
            'source': forms.Select(attrs={'class': 'form-select'}),
        }

