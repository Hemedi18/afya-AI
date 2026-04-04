from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _
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
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Jielezesha kwa ufupi...')}),
            'avatar': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['avatar'].label = _('Avatar')
        self.fields['bio'].label = _('Bio')


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['color_theme'].label = _('Color theme')
        self.fields['use_custom_palette'].label = _('Use custom colors')
        self.fields['custom_primary'].label = _('Custom primary')
        self.fields['custom_secondary'].label = _('Custom secondary')
        self.fields['background_style'].label = _('Background style')
        self.fields['background_intensity'].label = _('Background intensity')


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['privacy_mode'].label = _('Privacy mode')
        self.fields['privacy_mode'].help_text = _('Hide sensitive details on dashboard')

        self.fields['anonymous_mode'].label = _('Anonymous mode')
        self.fields['anonymous_mode'].help_text = _('Post to community anonymously by default')

        self.fields['emergency_alerts_enabled'].label = _('Emergency alerts')
        self.fields['emergency_alerts_enabled'].help_text = ''

        self.fields['reminder_period'].label = _('Period reminders')
        self.fields['reminder_period'].help_text = ''

        self.fields['reminder_ovulation'].label = _('Ovulation reminders')
        self.fields['reminder_ovulation'].help_text = ''

        self.fields['reminder_fertile_window'].label = _('Fertile window reminders')
        self.fields['reminder_fertile_window'].help_text = ''


class PersonaFullEditForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = [
            'birth_date', 'gender', 'height_cm', 'weight_kg',
            'health_notes', 'permanent_diseases', 'medications',
            'lifestyle_notes', 'sleep_hours', 'stress_level', 'exercise_frequency',
            'diet', 'goals', 'mental_health',
            'emergency_contact_name', 'emergency_contact_phone', 'location_region',
            'language_preference', 'ai_data_consent', 'identity_verified',
            'medical_info_verified', 'verification_notes',
        ]
        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
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
            'location_region': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Mfano: Dar es Salaam')}),
            'language_preference': forms.Select(
                attrs={'class': 'form-select'},
                choices=[('sw', _('Swahili')), ('en', _('English')), ('ar', _('Arabic'))],
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


class ForgotPasswordRequestForm(forms.Form):
    email = forms.EmailField(
        required=True,
        label=_('Email'),
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Weka email yako'),
                'autocomplete': 'email',
            }
        ),
    )

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError(_('Email is required.'))
        if not User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_('No account found with that email.'))
        return email


class ForgotPasswordResetForm(forms.Form):
    new_password1 = forms.CharField(
        label=_('New password'),
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Weka nenosiri jipya'),
                'autocomplete': 'new-password',
            }
        ),
        help_text=_('Use at least 8 characters.'),
    )
    new_password2 = forms.CharField(
        label=_('Confirm new password'),
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Rudia nenosiri jipya'),
                'autocomplete': 'new-password',
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('new_password1') or ''
        p2 = cleaned_data.get('new_password2') or ''

        if p1 and len(p1) < 8:
            self.add_error('new_password1', _('Password must be at least 8 characters.'))

        if p1 and p2 and p1 != p2:
            self.add_error('new_password2', _('Passwords do not match.'))

        return cleaned_data


class LanguagePreferenceForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = ['language_preference']
        widgets = {
            'language_preference': forms.Select(
                attrs={'class': 'form-select'},
                choices=[
                    ('sw', _('Kiswahili')),
                    ('en', _('English')),
                    ('ar', _('العربية')),
                ],
            )
        }


class ZanzHubRegisterForm(UserCreationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Andika username yako'),
                'autocomplete': 'username',
            }
        ),
        help_text=_('Tumia herufi, namba au alama @ . + - _ (max 150).'),
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Tengeneza nenosiri imara'),
                'autocomplete': 'new-password',
            }
        ),
        help_text=_('Angalau herufi 8; epuka nenosiri rahisi au la namba pekee.'),
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Rudia nenosiri lako'),
                'autocomplete': 'new-password',
            }
        ),
        help_text=_('Rudia nenosiri kwa uhakiki.'),
    )

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control form-control-lg',
                'placeholder': _('Weka barua pepe yako'),
                'autocomplete': 'email',
            }
        ),
        help_text=_('Barua pepe itatumika kama kitambulisho kikuu cha akaunti.'),
    )

    birth_date = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={
                'class': 'form-control form-control-lg',
                'type': 'date',
            }
        ),
        help_text=_('Tarehe ya kuzaliwa inahitajika.'),
    )

    gender = forms.ChoiceField(
        required=True,
        choices=UserAIPersona.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select form-select-lg'}),
        help_text=_('Jinsia inahitajika.'),
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'birth_date', 'gender', 'password1', 'password2')

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError(_('Email is required.'))
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_('This email is already in use.'))
        return email

    def clean_username(self):
        requested = (self.cleaned_data.get('username') or '').strip()
        base = requested or ((self.cleaned_data.get('email') or '').split('@')[0]) or 'user'
        base = base[:140]
        candidate = base
        counter = 1
        while User.objects.filter(username__iexact=candidate).exists():
            suffix = f"-{counter}"
            candidate = f"{base[:150 - len(suffix)]}{suffix}"
            counter += 1
        return candidate

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if not birth_date:
            raise forms.ValidationError(_('Birth date is required.'))
        from django.utils import timezone
        if birth_date > timezone.localdate():
            raise forms.ValidationError(_('Birth date cannot be in the future.'))
        return birth_date


class PersonaStepOneForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = ['birth_date', 'gender', 'height_cm', 'weight_kg']
        widgets = {
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'min': 100, 'max': 230}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': 25, 'max': 220}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['birth_date'].required = True
        self.fields['gender'].required = True
        self.fields['height_cm'].required = False
        self.fields['weight_kg'].required = False
        self.fields['gender'].choices = [('female', _('Female')), ('male', _('Male'))]


class PersonaStepTwoForm(forms.ModelForm):
    class Meta:
        model = UserAIPersona
        fields = ['health_notes', 'permanent_diseases', 'medications']
        widgets = {
            'health_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Mfano: pressure, allergy, operations za zamani...')}),
            'permanent_diseases': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Mfano: asthma, diabetes, none')}),
            'medications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Mfano: metformin, none')}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['health_notes'].required = False
        self.fields['permanent_diseases'].required = False
        self.fields['medications'].required = False


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
            'lifestyle_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Eleza maisha yako ya kila siku kwa ufupi...')}),
            'sleep_hours': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.5', 'min': 2, 'max': 14}),
            'stress_level': forms.Select(attrs={'class': 'form-select'}),
            'exercise_frequency': forms.Select(attrs={'class': 'form-select'}),
            'diet': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Optional: vegan, mixed, high-protein...')}),
            'goals': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Optional: lose weight, reduce pain, regular cycle...')}),
            'mental_health': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Optional: anxiety, low mood, panic history...')}),
            'ai_data_consent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['lifestyle_notes'].required = False
        self.fields['sleep_hours'].required = False
        self.fields['stress_level'].required = False
        self.fields['exercise_frequency'].required = False
        self.fields['ai_data_consent'].required = False
