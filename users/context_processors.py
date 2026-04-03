from .permissions import is_admin, is_doctor, is_moderator
from .utils import get_user_gender


def role_flags(request):
    user = getattr(request, 'user', None)
    user_gender = get_user_gender(user)
    avatar_url = ''
    avatar_version = ''
    user_initial = ''
    is_verified_doctor = False
    has_patient_logs = False
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
        # Verified doctor flag (used to show "Patients" nav link)
        try:
            dp = user.doctor_profile
            is_verified_doctor = bool(dp and dp.verified)
        except Exception:
            is_verified_doctor = False
        # Patient log flag (used to show "My Logs" nav link)
        if not is_verified_doctor:
            try:
                has_patient_logs = user.assigned_patient_logs.filter(
                    is_sent=True, is_active=True
                ).exists()
            except Exception:
                has_patient_logs = False
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
        'is_verified_doctor': is_verified_doctor,
        'has_patient_logs': has_patient_logs,
    }
