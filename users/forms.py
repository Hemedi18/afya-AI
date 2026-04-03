from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from .models import UserAIPersona
from menstrual.models import MenstrualUserSetting


class ProfileInfoForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class AvatarBioForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = ['avatar', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Jielezesha kwa ufupi...'}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }


class DisplayThemeForm(forms.ModelForm):
    class Meta:
        model = MenstrualUserSetting
        fields = [
            'color_theme',
            'use_custom_palette',
            'custom_primary',
            'custom_secondary',
            'background_style',
            'background_intensity',
        ]
        widgets = {
            'color_theme': forms.Select(attrs={'class': 'form-select'}),
            'use_custom_palette': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'custom_primary': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'custom_secondary': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'background_style': forms.Select(attrs={'class': 'form-select'}),
            'background_intensity': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 100}),
        }


class PrivacySettingsForm(forms.ModelForm):
    class Meta:
        model = MenstrualUserSetting
        fields = [
            'privacy_mode',
            'anonymous_mode',
            'emergency_alerts_enabled',
            'reminder_period',
            'reminder_ovulation',
            'reminder_fertile_window',
        ]
        widgets = {
            'privacy_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'anonymous_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'emergency_alerts_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reminder_period': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reminder_ovulation': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'reminder_fertile_window': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PersonaFullEditForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = [
            'age', 'gender', 'height_cm', 'weight_kg',
            'health_notes', 'permanent_diseases', 'medications',
            'lifestyle_notes', 'sleep_hours', 'stress_level', 'exercise_frequency',
            'diet', 'goals', 'mental_health',
            'emergency_contact_name', 'emergency_contact_phone', 'location_region',
            'language_preference', 'ai_data_consent', 'identity_verified',
            'medical_info_verified', 'verification_notes',
        ]
        widgets = {
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 90}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'min': 100, 'max': 230}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 25, 'max': 220}),
            'health_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'permanent_diseases': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'medications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'lifestyle_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'sleep_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': 2, 'max': 14}),
            'stress_level': forms.Select(attrs={'class': 'form-select'}),
            'exercise_frequency': forms.Select(attrs={'class': 'form-select'}),
            'diet': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'goals': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'mental_health': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'emergency_contact_name': forms.TextInput(attrs={'class': 'form-control'}),
            'emergency_contact_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+255...'}),
            'location_region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Mfano: Dar es Salaam'}),
            'language_preference': forms.Select(
                attrs={'class': 'form-select'},
                choices=[('sw', 'Swahili'), ('en', 'English'), ('ar', 'Arabic')],
            ),
            'ai_data_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'identity_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'medical_info_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'verification_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class ZanzPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = 'form-control'


class LanguagePreferenceForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = ['language_preference']
        widgets = {
            'language_preference': forms.Select(
                attrs={'class': 'form-select'},
                choices=[
                    ('sw', 'Kiswahili'),
                    ('en', 'English'),
                    ('ar', 'العربية'),
                ],
            )
        }


class ZanzHubRegisterForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Andika username yako',
                'autocomplete': 'username',
            }
        ),
        help_text='Tumia herufi, namba au alama @ . + - _ (max 150).',
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Tengeneza nenosiri imara',
                'autocomplete': 'new-password',
            }
        ),
        help_text='Angalau herufi 8; epuka nenosiri rahisi au la namba pekee.',
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': 'Rudia nenosiri lako',
                'autocomplete': 'new-password',
            }
        ),
        help_text='Rudia nenosiri kwa uhakiki.',
    )

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')


class PersonaStepOneForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = ['age', 'gender', 'height_cm', 'weight_kg']
        widgets = {
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 90}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'min': 100, 'max': 230}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 25, 'max': 220}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['age'].required = True
        self.fields['gender'].required = True
        self.fields['height_cm'].required = True
        self.fields['weight_kg'].required = True
        self.fields['gender'].choices = [('female', 'Female'), ('male', 'Male')]


class PersonaStepTwoForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = ['health_notes', 'permanent_diseases', 'medications']
        widgets = {
            'health_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mfano: pressure, allergy, operations za zamani...'}),
            'permanent_diseases': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mfano: asthma, diabetes, none'}),
            'medications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mfano: metformin, none'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['health_notes'].required = True
        self.fields['permanent_diseases'].required = True
        self.fields['medications'].required = True


class PersonaStepThreeForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = [
            'lifestyle_notes',
            'sleep_hours',
            'stress_level',
            'exercise_frequency',
            'diet',
            'goals',
            'mental_health',
            'ai_data_consent',
        ]
        widgets = {
            'lifestyle_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Eleza maisha yako ya kila siku kwa ufupi...'}),
            'sleep_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': 2, 'max': 14}),
            'stress_level': forms.Select(attrs={'class': 'form-select'}),
            'exercise_frequency': forms.Select(attrs={'class': 'form-select'}),
            'diet': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional: vegan, mixed, high-protein...'}),
            'goals': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional: lose weight, reduce pain, regular cycle...'}),
            'mental_health': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional: anxiety, low mood, panic history...'}),
            'ai_data_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lifestyle_notes'].required = True
        self.fields['sleep_hours'].required = True
        self.fields['stress_level'].required = True
        self.fields['exercise_frequency'].required = True
        self.fields['ai_data_consent'].required = True
