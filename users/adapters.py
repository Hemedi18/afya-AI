import re

from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import UserAIPersona


def _sanitize_username(value: str) -> str:
    value = (value or '').strip().lower()
    value = re.sub(r'[^a-z0-9._+-]+', '', value)
    return value[:150]


def _unique_username(seed: str, fallback: str = 'user') -> str:
    User = get_user_model()
    base = _sanitize_username(seed) or fallback
    candidate = base[:150]
    index = 1

    while User.objects.filter(username=candidate).exists():
        suffix = str(index)
        candidate = f'{base[:150 - len(suffix)]}{suffix}'
        index += 1

    return candidate


class AccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        if request.user.is_authenticated:
            user_email = (request.user.email or '').strip()
            social_verified = hasattr(request.user, 'socialaccount_set') and request.user.socialaccount_set.exists()
            email_verified = bool(
                user_email and EmailAddress.objects.filter(user=request.user, email__iexact=user_email, verified=True).exists()
            )
            if not (social_verified or email_verified):
                return reverse('account_email_verification_sent')
            persona, _created = UserAIPersona.objects.get_or_create(user=request.user)
            if not persona.onboarding_complete:
                return reverse('users:onboarding', kwargs={'step': 1})
        return reverse('main:home')


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_email_verified(self, request, email_address):
        # Social provider emails (Google, Facebook, X) are pre-verified
        # by the provider — no additional email confirmation needed.
        return True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        extra = sociallogin.account.extra_data or {}

        email = (data.get('email') or extra.get('email') or '').strip()
        first_name = (data.get('first_name') or extra.get('first_name') or '').strip()
        last_name = (data.get('last_name') or extra.get('last_name') or '').strip()
        name = (data.get('name') or extra.get('name') or '').strip()
        nickname = (data.get('username') or extra.get('username') or extra.get('screen_name') or '').strip()

        if email and not user.email:
            user.email = email
        if first_name and not user.first_name:
            user.first_name = first_name
        if last_name and not user.last_name:
            user.last_name = last_name

        if not user.username:
            seed = nickname or (email.split('@')[0] if email else '')
            if not seed:
                seed = name.replace(' ', '') if name else sociallogin.account.provider
            user.username = _unique_username(seed, fallback=sociallogin.account.provider)

        return user