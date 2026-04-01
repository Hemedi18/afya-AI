def get_user_gender(user):
    if not user or not user.is_authenticated:
        return None

    persona = getattr(user, 'ai_persona', None)
    if not persona or not persona.gender:
        return None

    gender = (persona.gender or '').strip().lower()
    if gender in {'female', 'male'}:
        return gender
    return None


def is_female_user(user):
    return get_user_gender(user) == 'female'


def is_male_user(user):
    return get_user_gender(user) == 'male'
