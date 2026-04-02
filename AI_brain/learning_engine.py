from .models import AIInteractionLog


def learn_from_feedback(user, feedback):
    """Store user feedback without schema changes."""
    if not feedback:
        return None

    payload = feedback if isinstance(feedback, dict) else {'feedback': str(feedback).strip()}

    return AIInteractionLog.objects.create(
        user=user,
        question='[USER_FEEDBACK]',
        reply='',
        context_payload={
            'feedback': payload,
            'kind': 'feedback',
        },
    )
