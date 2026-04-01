from django.conf import settings
from groq import Groq


def generate_ai_text(prompt: str, fallback: str) -> str:
    """Centralized AI text generation helper for the project."""
    api_key = getattr(settings, 'GROQ_API_KEY', None)
    if not api_key:
        return fallback

    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a women health AI assistant. Reply in simple Swahili, "
                        "empathetic, short, practical, and medically safe."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
        )
        return completion.choices[0].message.content.strip()
    except Exception:
        return fallback


def ask_ai_brain(message_text: str) -> str:
    """Simple wrapper used by integrations like SMS webhooks."""
    return generate_ai_text(
        prompt=message_text,
        fallback=(
            "Asante kwa ujumbe wako. Kwa sasa huduma ya AI imepumzika kidogo. "
            "Tafadhali jaribu tena baada ya muda mfupi."
        ),
    )
