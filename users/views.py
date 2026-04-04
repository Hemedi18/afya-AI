from django.conf import settings
from django.contrib.auth.views import LoginView
from django.shortcuts import render, redirect
from django.contrib.auth import login, update_session_auth_hash, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.utils.translation import gettext as _
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils import timezone
from urllib.parse import urlencode
import re
from django.db import transaction
import secrets
from datetime import date

try:
    from allauth.account.models import EmailAddress
except Exception:  # pragma: no cover
    EmailAddress = None

try:
    from allauth.account.utils import send_email_confirmation
    _ALLAUTH_SEND_EMAIL = True
except ImportError:
    _ALLAUTH_SEND_EMAIL = False

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


SOCIAL_PROVIDER_META = {
    'google': {
        'name': 'Google',
        'icon': 'bi-google',
        'url_name': 'google_login',
        'enabled_setting': 'GOOGLE_OAUTH_ENABLED',
        'missing_message': _('Google login is not configured yet. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in your environment.'),
    },
    'facebook': {
        'name': 'Facebook',
        'icon': 'bi-facebook',
        'url_name': 'facebook_login',
        'enabled_setting': 'FACEBOOK_OAUTH_ENABLED',
        'missing_message': _('Facebook login is not configured yet. Add FACEBOOK_APP_ID and FACEBOOK_APP_SECRET in your environment.'),
    },
    'twitter': {
        'name': 'X',
        'icon': 'bi-twitter-x',
        'url_name': 'twitter_oauth2_login',
        'enabled_setting': 'X_OAUTH_ENABLED',
        'missing_message': _('X login is not configured yet. Add X_CLIENT_ID and X_CLIENT_SECRET in your environment.'),
    },
}


def _build_social_providers(request):
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    providers = []

    for slug, meta in SOCIAL_PROVIDER_META.items():
        url = reverse('users:social_login', kwargs={'provider': slug})
        if next_url:
            url = f"{url}?{urlencode({'next': next_url})}"

        providers.append({
            'slug': slug,
            'name': meta['name'],
            'icon': meta['icon'],
            'url': url,
            'enabled': bool(getattr(settings, meta['enabled_setting'], False)),
        })

    return providers


class AfyaLoginView(LoginView):
    template_name = 'users/login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['social_providers'] = _build_social_providers(self.request)
        return context


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


def _user_email_is_verified(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    if not (user.email or '').strip():
        return False
    if EmailAddress is not None:
        if EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists():
            return True
    # Social providers are treated as pre-verified email identities
    if hasattr(user, 'socialaccount_set') and user.socialaccount_set.exists():
        return True
    return False


def _send_verification_email(request, user, signup=True):
    """Send allauth verification email and return (ok, error_message)."""
    try:
        if EmailAddress is not None:
            email_obj, _ = EmailAddress.objects.get_or_create(
                user=user,
                email=(user.email or '').strip(),
                defaults={
                    'verified': False,
                    'primary': True,
                },
            )
            if not email_obj.verified:
                email_obj.send_confirmation(request=request, signup=signup)
                return True, ''

        if _ALLAUTH_SEND_EMAIL:
            send_email_confirmation(request, user, signup=signup)
            return True, ''

        return False, _('Email verification service is not available.')
    except Exception as exc:
        return False, str(exc)


def _pending_signup_cache_key(token):
    return f'pending_signup:{token}'


def _queue_pending_signup(cleaned_data):
    token = secrets.token_urlsafe(32)
    otp = ''.join(secrets.choice('0123456789') for _ in range(6))
    now_ts = int(timezone.now().timestamp())
    payload = {
        'username': cleaned_data['username'],
        'email': cleaned_data['email'],
        'birth_date': cleaned_data['birth_date'].isoformat(),
        'gender': cleaned_data['gender'],
        'password': cleaned_data['password1'],
        'otp': otp,
        'otp_attempts': 0,
        'next_resend_at': now_ts + 30,
    }
    cache.set(_pending_signup_cache_key(token), payload, timeout=60 * 60 * 24)  # 24h
    return token


def _send_signup_otp_email(email, otp):
    subject = _('Your AfyaSmart verification code')
    text_body = (
        _('Welcome to AfyaSmart!') + '\n\n' +
        _('Use this OTP code to verify your email:') + '\n' +
        f'{otp}\n\n' +
        _('Code expires when the signup session expires (24 hours).')
    )
    html_body = (
        f"<p>{_('Welcome to AfyaSmart!')}</p>"
        f"<p>{_('Use this OTP code to verify your email:')}</p>"
        f"<p style=\"font-size:28px;font-weight:800;letter-spacing:4px;\">{otp}</p>"
        f"<p>{_('Code expires when the signup session expires (24 hours).')}</p>"
    )

    send_mail(
        subject=subject,
        message=text_body,
        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None),
        recipient_list=[email],
        fail_silently=False,
        html_message=html_body,
    )


def _get_pending_signup_payload(token):
    return cache.get(_pending_signup_cache_key(token))


def _save_pending_signup_payload(token, payload):
    cache.set(_pending_signup_cache_key(token), payload, timeout=60 * 60 * 24)

def register(request):
    if request.method == 'POST':
        form = ZanzHubRegisterForm(request.POST)
        if form.is_valid():
            try:
                token = _queue_pending_signup(form.cleaned_data)
                payload = _get_pending_signup_payload(token)
                _send_signup_otp_email(form.cleaned_data['email'], payload['otp'])
            except Exception as exc:
                form.add_error(None, _('Could not send verification email. Please check email settings and try again.'))
                form.add_error(None, str(exc))
                return render(request, 'users/register.html', {
                    'form': form,
                    'social_providers': _build_social_providers(request),
                })

            messages.success(request, _('OTP sent to your email. Enter it to complete signup.'))
            return redirect('users:verify_signup_otp', token=token)
    else:
        form = ZanzHubRegisterForm()
    return render(request, 'users/register.html', {
        'form': form,
        'social_providers': _build_social_providers(request),
    })


def verify_signup_otp(request, token):
    payload = _get_pending_signup_payload(token)
    if not payload:
        messages.error(request, _('Verification session is invalid or expired. Please register again.'))
        return redirect('users:register')

    email = (payload.get('email') or '').strip().lower()
    if not email:
        messages.error(request, _('Invalid verification data. Please register again.'))
        return redirect('users:register')

    now_ts = int(timezone.now().timestamp())

    if request.method != 'POST':
        seconds_left = max(0, int(payload.get('next_resend_at') or 0) - now_ts)
        return render(request, 'users/verify_signup_otp.html', {
            'email': email,
            'seconds_left': seconds_left,
        })

    if request.method == 'POST':
        action = (request.POST.get('action') or 'verify').strip()

        if action == 'resend':
            next_resend_at = int(payload.get('next_resend_at') or 0)
            if now_ts < next_resend_at:
                wait_for = next_resend_at - now_ts
                messages.warning(request, _('Please wait %(secs)s seconds before resending.') % {'secs': wait_for})
            else:
                new_otp = ''.join(secrets.choice('0123456789') for _ in range(6))
                payload['otp'] = new_otp
                payload['otp_attempts'] = 0
                payload['next_resend_at'] = now_ts + 30
                _save_pending_signup_payload(token, payload)
                try:
                    _send_signup_otp_email(email, new_otp)
                    messages.success(request, _('A new OTP has been sent to your email.'))
                except Exception as exc:
                    messages.error(request, str(exc))
            return redirect('users:verify_signup_otp', token=token)

        entered_otp = (request.POST.get('otp') or '').strip()
        if not entered_otp:
            messages.error(request, _('Please enter the OTP code.'))
            return redirect('users:verify_signup_otp', token=token)

        if entered_otp != str(payload.get('otp') or ''):
            payload['otp_attempts'] = int(payload.get('otp_attempts') or 0) + 1
            _save_pending_signup_payload(token, payload)
            remaining = max(0, 5 - payload['otp_attempts'])
            if payload['otp_attempts'] >= 5:
                cache.delete(_pending_signup_cache_key(token))
                messages.error(request, _('Too many incorrect OTP attempts. Please register again.'))
                return redirect('users:register')
            messages.error(request, _('Invalid OTP. You have %(count)s attempts left.') % {'count': remaining})
            return redirect('users:verify_signup_otp', token=token)

    # Only valid verify POST reaches this point.

    if User.objects.filter(email__iexact=email).exists():
        cache.delete(_pending_signup_cache_key(token))
        messages.info(request, _('This email already has an account. Please login.'))
        return redirect('users:login')

    with transaction.atomic():
        user = User.objects.create_user(
            username=payload['username'],
            email=email,
            password=payload['password'],
        )

        persona, _created = UserAIPersona.objects.get_or_create(user=user)
        birth_raw = (payload.get('birth_date') or '').strip()
        persona.birth_date = date.fromisoformat(birth_raw) if birth_raw else None
        persona.gender = payload.get('gender')
        persona.save()
        persona.update_quality_metrics(save=True)

        if EmailAddress is not None:
            EmailAddress.objects.update_or_create(
                user=user,
                email=email,
                defaults={'primary': True, 'verified': True},
            )

    cache.delete(_pending_signup_cache_key(token))
    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    messages.success(request, _('Email verified successfully. Complete your AI persona now.'))
    return redirect('users:onboarding', step=1)


def social_login_redirect(request, provider):
    meta = SOCIAL_PROVIDER_META.get(provider)
    if not meta:
        messages.error(request, _('That social login provider is not supported.'))
        return redirect('users:login')

    if not getattr(settings, meta['enabled_setting'], False):
        messages.error(request, meta['missing_message'])
        return redirect('users:login')

    next_url = request.GET.get('next') or ''
    target_url = reverse(meta['url_name'])
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target_url = f"{target_url}?{urlencode({'next': next_url})}"
    return redirect(target_url)


def check_username_availability(request):
    username = (request.GET.get('username') or '').strip()
    allowed_pattern = r'^[\w.@+-]+$'

    if not username:
        return JsonResponse({
            'ok': False,
            'available': False,
            'message': _('Andika username kwanza.'),
            'suggestions': [],
        })

    if len(username) < 3:
        return JsonResponse({
            'ok': True,
            'available': False,
            'message': _('Username iwe na angalau herufi 3.'),
            'suggestions': [],
        })

    if not re.match(allowed_pattern, username):
        return JsonResponse({
            'ok': True,
            'available': False,
            'message': _('Tumia herufi, namba au alama @ . + - _ pekee.'),
            'suggestions': [],
        })

    taken = User.objects.filter(username__iexact=username).exists()
    if not taken:
        return JsonResponse({
            'ok': True,
            'available': True,
            'message': _('Username inapatikana.'),
            'suggestions': [],
        })

    # Username can still be accepted; system auto-adjusts internally
    return JsonResponse({
        'ok': True,
        'available': True,
        'message': _('Username is already used; the system will auto-adjust it while keeping your preferred style.'),
        'suggestions': [],
    })


@login_required
def onboarding(request, step=1):
    if not _user_email_is_verified(request.user):
        sent_ok, send_err = _send_verification_email(request, request.user, signup=False)
        if sent_ok:
            messages.warning(request, _('Please verify your email first. We sent (or resent) a verification link.'))
        else:
            messages.error(request, _('Please verify your email first, but we could not send the verification link now. Check email settings and try again.'))
            if send_err:
                messages.error(request, send_err)
        return redirect('account_email_verification_sent')

    if step not in [1, 2, 3]:
        return redirect('users:onboarding', step=1)

    persona, _ = UserAIPersona.objects.get_or_create(user=request.user)

    step_map = {
        1: (PersonaStepOneForm, 'Basic info', 'Set your required essentials first: date of birth and gender.'),
        2: (PersonaStepTwoForm, 'Health info (optional)', 'You can fill this now or skip and complete later.'),
        3: (PersonaStepThreeForm, 'Lifestyle (optional)', 'Optional wellness details to improve personalization.'),
    }

    form_class, title, subtitle = step_map[step]
    next_url = request.GET.get('next') or request.POST.get('next') or ''
    if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        next_url = ''

    if request.method == 'POST':
        if request.POST.get('action') == 'skip':
            if next_url:
                return redirect(next_url)
            return redirect('main:services')

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
            return redirect('main:services')
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
