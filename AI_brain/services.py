from django.conf import settings
from groq import Groq
import requests
import logging
import json

logger = logging.getLogger(__name__)

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


def search_wikipedia(query: str, lang: str = 'en') -> tuple[str | None, str | None]:
    """Searches Wikipedia for a given query and returns (title, summary)."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    search_params = {
        "action": "query",
        "format": "json",
        "list": "search",
        "srsearch": query,
        "srlimit": 1
    }
    try:
        response = requests.get(url, params=search_params, timeout=10)
        response.raise_for_status()
        data = response.json()
        search_results = data.get("query", {}).get("search", [])

        if search_results:
            page_title = search_results[0]["title"]
            content_params = {
                "action": "query",
                "format": "json",
                "prop": "extracts",
                "exintro": True,
                "explaintext": True,
                "titles": page_title,
                "exsentences": 4
            }
            content_response = requests.get(url, params=content_params, timeout=10)
            content_response.raise_for_status()
            content_data = content_response.json()
            pages = content_data.get("query", {}).get("pages", {})
            page_id = next(iter(pages))
            extract = pages[page_id].get("extract", "No summary found.")
            return page_title, extract
    except Exception as e:
        logger.error(f"Wikipedia search error for {query}: {e}")
    return None, None


def get_disease_info_from_external_apis(user_query: str) -> dict:
    """
    Orchestrates the flow: AI name correction -> Wikipedia search -> AI Synthesis.
    Returns structured disease information.
    """
    # Step 1: AI to get the formal English medical name for better API accuracy
    correction_prompt = (
        f"Toa jina la kitaalamu la ugonjwa huu kwa Kiingereza (Medical Name): '{user_query}'. "
        "Andika jina pekee bila maelezo mengine."
    )
    formal_name = generate_ai_text(correction_prompt, user_query).strip().strip('.')

    # Step 2: Search Wikipedia (often acts as a repository for WHO/CDC data)
    wiki_title, wiki_summary = search_wikipedia(formal_name)
    
    # Step 3: Use AI to synthesize into the 15-point structure in JSON format
    ai_synthesis_prompt = (
        f"Wewe ni mtaalamu wa afya wa kiwango cha juu. Changanua ugonjwa huu: '{formal_name}'.\n"
        f"Data ya ziada (Wikipedia): {wiki_summary or 'Hazijapatikana'}.\n\n"
        "Tengeneza ripoti kamili kwa Kiswahili kwa kutumia mfumo wa JSON pekee wenye key hizi 15:\n"
        "1. basic_info (name_sw, alt_names, category, body_system, severity, risk_level_ai)\n"
        "2. description (definition, mechanism, impact)\n"
        "3. causes (bacterial, viral, genetic, lifestyle, environmental)\n"
        "4. symptoms (common, early, severe, emergency)\n"
        "5. risk_factors (list items)\n"
        "6. treatment_options (medication, lifestyle, therapy, surgery, home_care)\n"
        "7. common_medications (list of dicts with: name, dosage, frequency, side_effects, warnings)\n"
        "8. prevention (lifestyle, diet, exercise, vaccination, avoidance)\n"
        "9. complications (long_term, organ_damage, disability, fatal_risk)\n"
        "10. emergency_signs (when_to_seek_doctor)\n"
        "11. monitoring (symptoms, pain, bp, sugar, temp, oxygen)\n"
        "12. ai_insights (risk_score, severity_score, progression, alerts)\n"
        "13. clinical_info (lab_tests, imaging, physical_exam)\n"
        "14. recovery_info (time, chronic_vs_temp, management)\n"
        "15. lifestyle_advice (diet, exercise, sleep)\n\n"
        "Hakikisha majibu yote ni kwa Kiswahili sanifu na rahisi. Usitoe hofu."
    )
    
    json_response = generate_ai_text(ai_synthesis_prompt, "{}")
    
    try:
        # Safisha JSON kama kuna markdown backticks
        if "```json" in json_response:
            json_response = json_response.split("```json")[1].split("```")[0].strip()
        elif "```" in json_response:
            json_response = json_response.split("```")[1].split("```")[0].strip()
            
        structured_data = json.loads(json_response)
    except Exception as e:
        logger.error(f"Failed to parse AI JSON for disease {formal_name}: {e}")
        structured_data = {}

    # Fallback for display names if JSON failed
    name_sw = structured_data.get('basic_info', {}).get('name_sw', user_query)
    if not structured_data:
        # In case of total failure, provide a minimal fallback
        structured_data = {"error": "Mchakato wa AI umeshindwa. Tafadhali jaribu tena."}

    return {
        "disease_name_en": formal_name,
        "disease_name_sw": name_sw,
        "structured_data": structured_data,
        "wikipedia_summary_en": wiki_summary or "Wikipedia data unavailable.",
    }
