from django.conf import settings
from groq import Groq
import requests

try:
    import ollama
except Exception:  # pragma: no cover - optional runtime dependency behavior
    ollama = None


def _generate_with_ollama(prompt: str) -> str | None:
    if ollama is None:
        return None

    model = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:3b')
    host = getattr(settings, 'OLLAMA_HOST', 'http://127.0.0.1:11434')

    try:
        client = ollama.Client(host=host)
        response = client.chat(
            model=model,
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are a women health AI assistant. Reply in simple Swahili, '
                        'empathetic, short, practical, and medically safe.'
                    ),
                },
                {'role': 'user', 'content': prompt},
            ],
            options={'temperature': 0.4},
        )
        content = (((response or {}).get('message') or {}).get('content') or '').strip()
        return content or None
    except Exception:
        return None


def _generate_with_openrouter(prompt: str) -> str | None:
    api_key = getattr(settings, 'OPENROUTER_API_KEY', None)
    if not api_key:
        return None

    model = getattr(settings, 'OPENROUTER_MODEL', 'qwen/qwen-2.5-72b-instruct:free')
    try:
        response = requests.post(
            'https://openrouter.ai/api/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': model,
                'messages': [
                    {
                        'role': 'system',
                        'content': (
                            'You are a women health AI assistant. Reply in simple Swahili, '
                            'empathetic, short, practical, and medically safe.'
                        ),
                    },
                    {'role': 'user', 'content': prompt},
                ],
                'temperature': 0.4,
            },
            timeout=40,
        )
        if response.status_code >= 400:
            return None
        data = response.json() or {}
        content = (((data.get('choices') or [{}])[0].get('message') or {}).get('content') or '').strip()
        return content or None
    except Exception:
        return None


def _generate_with_groq(prompt: str) -> str | None:
    api_key = getattr(settings, 'GROQ_API_KEY', None)
    if not api_key:
        return None

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
        return None


def transcribe_audio_file(uploaded_file) -> str | None:
    """Transcribe uploaded audio using Groq Whisper-compatible endpoint."""
    api_key = getattr(settings, 'GROQ_API_KEY', None)
    if not api_key or not uploaded_file:
        return None

    max_size = 15 * 1024 * 1024
    try:
        if getattr(uploaded_file, 'size', 0) and uploaded_file.size > max_size:
            return None
        uploaded_file.seek(0)
        payload = uploaded_file.read()
        if not payload:
            return None
        client = Groq(api_key=api_key)
        transcription = client.audio.transcriptions.create(
            file=(getattr(uploaded_file, 'name', 'voice-message.webm'), payload),
            model='whisper-large-v3-turbo',
            prompt=(
                'Transcribe this health voice note carefully. Preserve Swahili words, '
                'medical symptoms, time expressions, and short mixed English phrases.'
            ),
            language='sw',
            temperature=0,
        )
        text = getattr(transcription, 'text', None)
        if not text and isinstance(transcription, dict):
            text = transcription.get('text')
        return (text or '').strip() or None
    except Exception:
        return None


def generate_ai_text(prompt: str, fallback: str) -> str:
    """Centralized AI text generation helper for the project."""
    provider = getattr(settings, 'AI_PROVIDER', 'groq').lower()

    if provider == 'openrouter':
        return _generate_with_openrouter(prompt) or _generate_with_groq(prompt) or _generate_with_ollama(prompt) or fallback

    if provider == 'ollama':
        return _generate_with_ollama(prompt) or _generate_with_groq(prompt) or _generate_with_openrouter(prompt) or fallback

    # default: groq
    return _generate_with_groq(prompt) or _generate_with_openrouter(prompt) or _generate_with_ollama(prompt) or fallback


def ask_ai_brain(message_text: str) -> str:
    """Simple wrapper used by integrations like SMS webhooks."""
    return generate_ai_text(
        prompt=message_text,
        fallback=(
            "Samahani, kwa sasa AI haijapatikana. Kwa usalama wako, fuatilia dalili zako "
            "na wasiliana na daktari kama maumivu ni makali."
        ),
    )
