from .models import AIInteractionLog


def get_last_symptom(user):
    last = AIInteractionLog.objects.filter(user=user).order_by('-created_at').first()
    if not last:
        return None
    payload = last.context_payload or {}
    return payload.get('symptom_detected')
