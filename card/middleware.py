from django.utils import timezone

from .models import ensure_persona_update_notification


class PersonaReminderMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            today_key = f"persona_checked_{timezone.localdate().isoformat()}"
            if not request.session.get(today_key):
                ensure_persona_update_notification(request.user)
                request.session[today_key] = True
        return self.get_response(request)
