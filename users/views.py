from django.shortcuts import render, redirect
from django.contrib.auth import login, update_session_auth_hash, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from urllib.parse import urlencode

from .forms import (
    ZanzHubRegisterForm,
    PersonaStepOneForm,
    PersonaStepTwoForm,
    PersonaStepThreeForm,
    ProfileInfoForm,
    AvatarBioForm,
    PersonaFullEditForm,
    ZanzPasswordChangeForm,
)
from .models import UserAIPersona, PersonaDataSnapshot
from .utils import get_user_gender


def _store_persona_snapshot(user, persona, source='profile_update'):
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

def register(request):
    if request.method == 'POST':
        form = ZanzHubRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # Ingia ndani moja kwa moja baada ya kujisajili
            return redirect('users:onboarding', step=1)
    else:
        form = ZanzHubRegisterForm()
    return render(request, 'users/register.html', {'form': form})


@login_required
def onboarding(request, step=1):
    if step not in [1, 2, 3]:
        return redirect('users:onboarding', step=1)

    persona, _ = UserAIPersona.objects.get_or_create(user=request.user)

    step_map = {
        1: (PersonaStepOneForm, 'Basic info', 'Weka taarifa zako za msingi kwanza.'),
        2: (PersonaStepTwoForm, 'Health info', 'Weka historia fupi ya afya kwa personalization sahihi.'),
        3: (PersonaStepThreeForm, 'Lifestyle', 'Malizia na mtindo wa maisha, malengo, na afya ya akili (optional sehemu).'),
    }

    form_class, title, subtitle = step_map[step]
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = ''

    if request.method == 'POST':
        form = form_class(request.POST, instance=persona)
        if form.is_valid():
            persona = form.save()
            persona.update_quality_metrics(save=True)
            _store_persona_snapshot(request.user, persona, source='onboarding')
            if step < 3:
                if next_url:
                    next_step_url = reverse('users:onboarding', kwargs={'step': step + 1})
                    return redirect(f"{next_step_url}?{urlencode({'next': next_url})}")
                return redirect('users:onboarding', step=step + 1)
            messages.success(request, 'Asante! AI persona yako imekamilika na sasa majibu yatakuwa personalized zaidi.')
            if next_url:
                return redirect(next_url)
            return redirect('main:home')
    else:
        form = form_class(instance=persona)

    return render(
        request,
        'users/onboarding.html',
        {
            'form': form,
            'step': step,
            'step_title': title,
            'step_subtitle': subtitle,
            'progress': int((step / 3) * 100),
            'next_url': next_url,
        },
    )


@login_required
def profile(request):
    persona, _ = UserAIPersona.objects.get_or_create(user=request.user)

    info_form = ProfileInfoForm(instance=request.user)
    avatar_form = AvatarBioForm(instance=persona)
    persona_form = PersonaFullEditForm(instance=persona)
    password_form = ZanzPasswordChangeForm(user=request.user)

    active_tab = request.GET.get('tab', 'account')

    if request.method == 'POST':
        action = request.POST.get('_action')

        if action == 'update_info':
            info_form = ProfileInfoForm(request.POST, instance=request.user)
            avatar_form = AvatarBioForm(request.POST, request.FILES, instance=persona)
            if info_form.is_valid() and avatar_form.is_valid():
                info_form.save()
                avatar_form.save()
                messages.success(request, 'Taarifa zako zimehifadhiwa!')
                return redirect(f'{request.path}?tab=account')
            if avatar_form.errors.get('avatar'):
                messages.error(request, f"Picha haikuhifadhiwa: {avatar_form.errors['avatar'][0]}")
            else:
                messages.error(request, 'Imeshindikana kuhifadhi mabadiliko ya profile. Tafadhali angalia taarifa ulizoingiza.')
            active_tab = 'account'

        elif action == 'update_persona':
            persona_form = PersonaFullEditForm(request.POST, instance=persona)
            if persona_form.is_valid():
                persona = persona_form.save()
                persona.update_quality_metrics(save=True)
                _store_persona_snapshot(request.user, persona, source='profile_update')
                messages.success(request, 'AI Persona yako imesasishwa!')
                return redirect(f'{request.path}?tab=persona')
            active_tab = 'persona'

        elif action == 'change_password':
            password_form = ZanzPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                password_form.save()
                update_session_auth_hash(request, password_form.user)
                messages.success(request, 'Nenosiri limebadilishwa kwa mafanikio!')
                return redirect(f'{request.path}?tab=security')
            active_tab = 'security'

    return render(request, 'users/profile.html', {
        'info_form': info_form,
        'avatar_form': avatar_form,
        'persona_form': persona_form,
        'password_form': password_form,
        'persona': persona,
        'active_tab': active_tab,
    })


def logout_view(request):
    if request.method == 'POST':
        auth_logout(request)
        messages.success(request, 'Umeondoka kwa mafanikio. Karibu tena!')
    return redirect('main:home')
