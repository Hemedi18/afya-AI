from django import forms
from django.contrib.auth.models import Group
from django.contrib.auth.models import User
from django.db import transaction

from menstrual.models import DoctorProfile
from .models import DoctorVerificationDocument, DoctorVerificationRequest
from users.permissions import DOCTOR_GROUP


class DoctorRegistrationForm(forms.Form):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={'class': 'form-control'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    first_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    last_name = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    gender = forms.ChoiceField(choices=DoctorProfile.GENDER_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))
    specialization = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    hospital_name = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    bio = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}))
    license_number = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'class': 'form-control'}))
    issuing_body = forms.CharField(max_length=150, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    verification_document = forms.FileField(widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control'}))

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Username tayari imetumika.')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Email tayari imesajiliwa.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('password1') != cleaned_data.get('password2'):
            raise forms.ValidationError('Passwords hazifanani.')
        return cleaned_data

    @transaction.atomic
    def save(self):
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            first_name=self.cleaned_data.get('first_name', ''),
            last_name=self.cleaned_data.get('last_name', ''),
            password=self.cleaned_data['password1'],
        )
        doctor_group, _ = Group.objects.get_or_create(name=DOCTOR_GROUP)
        user.groups.add(doctor_group)

        profile = DoctorProfile.objects.create(
            user=user,
            gender=self.cleaned_data['gender'],
            specialization=self.cleaned_data['specialization'],
            hospital_name=self.cleaned_data.get('hospital_name', ''),
            bio=self.cleaned_data['bio'],
            verified=False,
        )

        verification_request = DoctorVerificationRequest.objects.create(
            doctor_profile=profile,
            license_number=self.cleaned_data['license_number'],
            issuing_body=self.cleaned_data.get('issuing_body', ''),
        )
        DoctorVerificationDocument.objects.create(
            verification_request=verification_request,
            title='Professional verification document',
            document=self.cleaned_data['verification_document'],
        )
        return user
