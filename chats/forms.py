from django import forms
from django.core.validators import FileExtensionValidator
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

from menstrual.models import CommunityGroup


class PrivateConversationStartForm(forms.Form):
    subject = forms.CharField(
        max_length=180,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Mfano: Maumivu makali ya tumbo')}),
    )
    opening_message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': _('Eleza tatizo lako kwa kifupi...')}),
    )


class PrivateMessageForm(forms.Form):
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Andika ujumbe wako...')}),
    )
    attachment = forms.FileField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))

    def clean(self):
        cleaned = super().clean()
        content = (cleaned.get('content') or '').strip()
        attachment = cleaned.get('attachment')
        if not content and not attachment:
            raise forms.ValidationError(_('Andika ujumbe au chagua attachment.'))
        
        # Validate file size (max 100MB)
        if attachment and isinstance(attachment, UploadedFile):
            max_size = 100 * 1024 * 1024  # 100MB
            if attachment.size and attachment.size > max_size:
                raise forms.ValidationError(_('Faili ni kubwa sana. Max: 100MB, Yako: %(size).1fMB') % {'size': attachment.size / (1024*1024)})
        
        cleaned['content'] = content
        return cleaned


class ContentReportForm(forms.Form):
    reason = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Sababu ya report')}),
    )
    details = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': _('Maelezo ya ziada...')}),
    )


class CommunityGroupForm(forms.ModelForm):
    send_admin_preview = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label=_('Send for admin preview'),
    )
    preview_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Maelezo kwa admin kuhusu group hii...')}),
        label=_('Preview note'),
    )

    class Meta:
        model = CommunityGroup
        fields = ['name', 'description', 'image', 'require_join_approval']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Mfano: Afya na Lishe')}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Lengo la group hii...')}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'require_join_approval': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class CommunityStatusForm(forms.Form):
    content = forms.CharField(
        max_length=250,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Status yako ya leo...')}),
    )
    image = forms.ImageField(required=False, widget=forms.ClearableFileInput(attrs={'class': 'form-control'}))
    group_id = forms.IntegerField(required=False, widget=forms.HiddenInput())


class ClarificationRequestForm(forms.Form):
    target_role = forms.ChoiceField(
        choices=[('doctor', _('Doctor')), ('admin', _('Admin')), ('group_admin', _('Group Admin Preview'))],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    doctor_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    question = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Eleza unachotaka kufafanuliwa...')}),
    )

    def clean(self):
        cleaned_data = super().clean()
        target_role = cleaned_data.get('target_role')
        doctor_id = cleaned_data.get('doctor_id')
        if target_role == 'doctor' and not doctor_id:
            raise forms.ValidationError(_('Chagua daktari unayetaka akujibu.'))
        return cleaned_data
