import re

from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.utils import translation
from django.utils.translation import gettext as _

from users.models import UserAIPersona, PersonaDataSnapshot
from .forms import (
    ProfileInfoForm,
    AvatarBioForm,
    DisplayThemeForm,
    PersonaFullEditForm,
    ZanzPasswordChangeForm,
    LanguagePreferenceForm,
    PrivacySettingsForm,
)
from django.contrib.auth import update_session_auth_hash
from menstrual.models import MenstrualUserSetting


def _store_persona_snapshot(user, persona, source='settings_update'):
    PersonaDataSnapshot.objects.create(
        user=user,
        persona=persona,
        source=source,
        completeness_score=persona.profile_completeness_score,
        identity_verified=persona.identity_verified,
        medical_info_verified=persona.medical_info_verified,
        payload={
            'onboarding_complete': persona.onboarding_complete,
            'language_preference': persona.language_preference,
            'region': persona.location_region,
            'stress_level': persona.stress_level,
            'exercise_frequency': persona.exercise_frequency,
            'ai_data_consent': persona.ai_data_consent,
        },
    )


class UserSettingsView(LoginRequiredMixin, View):
    template_name = 'users/settings.html'

    @staticmethod
    def _sections():
        return [
            {'id': 'general', 'title': _('General Settings'), 'icon': 'bi-sliders'},
            {'id': 'display', 'title': _('Display & Profile'), 'icon': 'bi-palette'},
            {'id': 'security', 'title': _('Security & Privacy'), 'icon': 'bi-shield-lock'},
            {'id': 'language', 'title': _('Language'), 'icon': 'bi-translate'},
        ]

    def get(self, request, section='general'):
        persona, _created_persona = UserAIPersona.objects.get_or_create(user=request.user)
        settings_obj, _created_settings = MenstrualUserSetting.objects.get_or_create(user=request.user)
        
        forms = {
            'general': ProfileInfoForm(instance=request.user),
            'display': AvatarBioForm(instance=persona),
            'display_theme': DisplayThemeForm(instance=settings_obj, prefix='theme'),
            'security': ZanzPasswordChangeForm(user=request.user),
            'privacy': PrivacySettingsForm(instance=settings_obj),
            'language': LanguagePreferenceForm(instance=persona),
        }
        
        context = {
            'active_section': section,
            'persona': persona,
            'forms': forms,
            'sections': self._sections(),
        }
        return render(request, self.template_name, context)

    def post(self, request, section='general'):
        persona, _created_persona = UserAIPersona.objects.get_or_create(user=request.user)
        settings_obj, _created_settings = MenstrualUserSetting.objects.get_or_create(user=request.user)
        
        action = request.POST.get('_action', section)
        success_msg = ''
        
        if action == 'general':
            form = ProfileInfoForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                success_msg = _('General settings updated successfully!')
            else:
                return self._render_with_errors(request, section, {'general': form})
        
        elif action == 'display':
            form = AvatarBioForm(request.POST, request.FILES, instance=persona)
            theme_form = DisplayThemeForm(request.POST, instance=settings_obj, prefix='theme')
            if form.is_valid() and theme_form.is_valid():
                form.save()
                theme_form.save()
                success_msg = _('Display settings updated!')
            else:
                return self._render_with_errors(request, section, {'display': form, 'display_theme': theme_form})
        
        elif action == 'security':
            form = ZanzPasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)
                success_msg = _('Password changed successfully!')
            else:
                return self._render_with_errors(request, section, {'security': form})

        elif action == 'privacy':
            form = PrivacySettingsForm(request.POST, instance=settings_obj)
            if form.is_valid():
                form.save()
                success_msg = _('Privacy settings updated successfully!')
            else:
                return self._render_with_errors(request, section, {'privacy': form})

        elif action == 'language':
            form = LanguagePreferenceForm(request.POST, instance=persona)
            if form.is_valid():
                form.save()
                selected_language = form.cleaned_data['language_preference']
                response = redirect(self._localized_redirect_path(request.path, selected_language))
                translation.activate(selected_language)
                request.session[translation.LANGUAGE_SESSION_KEY] = selected_language
                response.set_cookie(
                    settings.LANGUAGE_COOKIE_NAME,
                    selected_language,
                    max_age=365 * 24 * 60 * 60,
                    samesite='Lax',
                )
                messages.success(request, _('Language updated successfully!'))
                return response
            else:
                return self._render_with_errors(request, section, {'language': form})
        
        if success_msg:
            messages.success(request, success_msg)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, 'message': success_msg})
            return redirect(f'{request.path}?section={action}')
        
        return self._render_with_errors(request, section, {action: form})

    def _render_with_errors(self, request, section, form_dict):
        persona, _created_persona = UserAIPersona.objects.get_or_create(user=request.user)
        settings_obj, _created_settings = MenstrualUserSetting.objects.get_or_create(user=request.user)
        forms = {
            'general': form_dict.get('general', ProfileInfoForm(instance=request.user)),
            'display': form_dict.get('display', AvatarBioForm(instance=persona)),
            'display_theme': form_dict.get('display_theme', DisplayThemeForm(instance=settings_obj, prefix='theme')),
            'security': form_dict.get('security', ZanzPasswordChangeForm(user=request.user)),
            'privacy': form_dict.get('privacy', PrivacySettingsForm(instance=settings_obj)),
            'language': form_dict.get('language', LanguagePreferenceForm(instance=persona)),
        }
        
        context = {
            'active_section': section,
            'persona': persona,
            'forms': forms,
            'sections': self._sections(),
        }
        return render(request, self.template_name, context)

    def _localized_redirect_path(self, current_path, language_code):
        language_codes = [code for code, _label in settings.LANGUAGES]
        pattern = rf"^/({'|'.join(language_codes)})(/|$)"
        if re.match(pattern, current_path):
            return re.sub(pattern, f"/{language_code}/", current_path, count=1)
        return f"/{language_code}{current_path if current_path.startswith('/') else '/' + current_path}"
