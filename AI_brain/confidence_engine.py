def calculate_confidence(persona, history_context, symptom):
    score = 0

    if getattr(persona, 'profile_completeness_score', 0) > 70:
        score += 30

    if history_context and (history_context.get('top_symptoms') or history_context.get('log_symptoms')):
        score += 20

    if symptom:
        score += 30

    if getattr(persona, 'medical_info_verified', False):
        score += 20

    return min(score, 100)
