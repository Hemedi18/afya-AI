from collections import Counter

from menstrual.models import DailyLog
from .models import AIInteractionLog


def build_user_history_context(user):
    interactions = AIInteractionLog.objects.filter(user=user).order_by('-created_at')[:20]

    past_symptoms = []
    for item in interactions:
        payload = item.context_payload or {}
        symptom = payload.get('symptom_detected')
        if symptom:
            past_symptoms.append(symptom)

    top_symptoms = Counter(past_symptoms).most_common(3)

    logs = DailyLog.objects.filter(cycle__user=user).order_by('-date')[:30]
    log_symptoms = []
    for log in logs:
        for val in (log.physical_symptoms or []):
            if isinstance(val, str) and val.strip():
                log_symptoms.append(val.strip().lower())

    common_log_symptoms = Counter(log_symptoms).most_common(5)

    return {
        'top_symptoms': top_symptoms,
        'log_symptoms': common_log_symptoms,
    }
