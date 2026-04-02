from .services import generate_ai_text


def generate_differential(question, history):
    prompt = f"""
You are a medical diagnostic AI.

User symptoms:
{question}

User history:
{history}

Provide:
1. Possible conditions
2. Most likely condition
3. Risk level (LOW/MEDIUM/HIGH)

Keep medically safe and concise in simple Swahili.
""".strip()

    fallback = (
        'Uchambuzi wa awali: kuna sababu zaidi ya moja. '
        'Endelea na maswali ya ufafanuzi ili kupunguza options.'
    )

    return generate_ai_text(prompt, fallback)
