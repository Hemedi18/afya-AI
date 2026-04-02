from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse

from users.models import UserAIPersona, PersonaDataSnapshot
from .forms import (
    ProfileInfoForm,
    AvatarBioForm,
    PersonaFullEditForm,
    ZanzPasswordChangeForm,
)
from django.contrib.auth import update_session_auth_hash


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

    def get(self, request, section='general'):
        persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
        
        forms = {
            'general': ProfileInfoForm(instance=request.user),
            'display': AvatarBioForm(instance=persona),
            'security': ZanzPasswordChangeForm(user=request.user),
        }
        
        context = {
            'active_section': section,
            'persona': persona,
            'forms': forms,
            'sections': [
                {'id': 'general', 'title': 'General Settings', 'icon': 'bi-sliders'},
                {'id': 'display', 'title': 'Display & Profile', 'icon': 'bi-palette'},
                {'id': 'security', 'title': 'Security & Privacy', 'icon': 'bi-shield-lock'},
            ],
        }
        return render(request, self.template_name, context)

    def post(self, request, section='general'):
        persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
        
        action = request.POST.get('_action', section)
        success_msg = ''
        
        if action == 'general':
            form = ProfileInfoForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                success_msg = 'General settings updated successfully!'
            else:
                return self._render_with_errors(request, section, {'general': form})
        
        elif action == 'display':
            form = AvatarBioForm(request.POST, request.FILES, instance=persona)
            if form.is_valid():
                form.save()
                success_msg = 'Display settings updated!'
            else:
                return self._render_with_errors(request, section, {'display': form})
        
        elif action == 'security':
            form = ZanzPasswordChangeForm(user=request.user, data=request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)
                success_msg = 'Password changed successfully!'
            else:
                return self._render_with_errors(request, section, {'security': form})
        
        if success_msg:
            messages.success(request, success_msg)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'ok': True, 'message': success_msg})
            return redirect(f'{request.path}?section={action}')
        
        return self._render_with_errors(request, section, {action: form})

    def _render_with_errors(self, request, section, form_dict):
        persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
        forms = {
            'general': form_dict.get('general', ProfileInfoForm(instance=request.user)),
            'display': form_dict.get('display', AvatarBioForm(instance=persona)),
            'security': form_dict.get('security', ZanzPasswordChangeForm(user=request.user)),
        }
        
        context = {
            'active_section': section,
            'persona': persona,
            'forms': forms,
            'sections': [
                {'id': 'general', 'title': 'General Settings', 'icon': 'bi-sliders'},
                {'id': 'display', 'title': 'Display & Profile', 'icon': 'bi-palette'},
                {'id': 'security', 'title': 'Security & Privacy', 'icon': 'bi-shield-lock'},
            ],
        }
        return render(request, self.template_name, context)
