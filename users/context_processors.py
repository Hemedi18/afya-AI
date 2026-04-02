from .permissions import is_admin, is_doctor, is_moderator
from .utils import get_user_gender


def role_flags(request):
    user = getattr(request, 'user', None)
    user_gender = get_user_gender(user)
    avatar_url = ''
    avatar_version = ''
    user_initial = ''
    if getattr(user, 'is_authenticated', False):
        user_initial = (getattr(user, 'username', '')[:1] or '?').upper()
        persona = getattr(user, 'ai_persona', None)
        if persona and getattr(persona, 'avatar', None):
            try:
                avatar_url = persona.avatar.url
                if getattr(persona, 'updated_at', None):
                    avatar_version = int(persona.updated_at.timestamp())
            except ValueError:
                avatar_url = ''
    return {
        'is_admin_user': is_admin(user),
        'is_doctor_user': is_doctor(user),
        'is_moderator_user': is_moderator(user),
        'user_gender': user_gender,
        'is_female_user': user_gender == 'female',
        'is_male_user': user_gender == 'male',
        'current_user_avatar_url': avatar_url,
        'current_user_avatar_version': avatar_version,
        'current_user_initial': user_initial,
    }
