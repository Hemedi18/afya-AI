from .services import generate_ai_text


def multi_step_diagnosis(question, history, risk):
    prompt = f"""
You are a clinical diagnostic AI.

User symptoms:
{question}

User history:
{history}

Risk level:
{risk}

Step 1: Identify possible conditions
Step 2: Identify most likely condition
Step 3: Suggest next clarification questions if needed
Step 4: Give safe advice

Respond in simple Swahili.
""".strip()

    fallback = (
        'Ninaendelea na uchambuzi wa hatua kwa hatua. '
        'Tafadhali jibu maswali ya ufafanuzi kwa usahihi.'
    )

    return generate_ai_text(prompt, fallback)
