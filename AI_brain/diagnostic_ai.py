from .services import generate_ai_text


def _persona_snapshot(persona):
    fields = []
    if getattr(persona, 'age', None):
        fields.append(f"Age: {persona.age}")
    if getattr(persona, 'gender', None):
        fields.append(f"Gender: {persona.gender}")
    if getattr(persona, 'permanent_diseases', None):
        fields.append(f"Chronic diseases: {persona.permanent_diseases}")
    if getattr(persona, 'medications', None):
        fields.append(f"Current medication: {persona.medications}")
    if getattr(persona, 'health_notes', None):
        fields.append(f"Health notes: {persona.health_notes}")
    if not fields:
        return "No strong profile data available."
    return "\n".join(f"- {item}" for item in fields)


def generate_diagnostic_questions(question, persona, signal_block, symptom_hint=''):
    persona_text = _persona_snapshot(persona)
    signal_text = signal_block or "No recent logs available."

    prompt = f"""
You are a medical diagnostic AI assistant.

User question:
{question}

Symptom hint:
{symptom_hint or 'unknown'}

User health profile:
{persona_text}

Recent health signals:
{signal_text}

Your task:
1. Identify likely differential paths internally.
2. Generate ONLY 3-6 clarification questions.
3. Each line MUST be a question ending with '?'
4. No advice. No explanations. No diagnosis text.
5. Questions must be simple, medically relevant, safe.
""".strip()

    fallback = "\n".join([
        "Je maumivu yalianza lini?",
        "Je maumivu ni makali kiasi gani (1-10)?",
        "Je una dalili nyingine kama homa, kutapika, au kuharisha?",
    ])

    response = generate_ai_text(prompt, fallback)
    questions = [line.strip() for line in (response or '').split("\n") if line.strip()]

    merged = []
    buffer = ""
    for part in questions:
        text = part.lstrip("-•0123456789. ").strip()
        if not text:
            continue
        if buffer:
            buffer = f"{buffer} {text}".strip()
        else:
            buffer = text
        if buffer.endswith('?'):
            merged.append(buffer)
            buffer = ""
    if buffer:
        merged.append(buffer.rstrip(' .,:;!') + '?')

    cleaned = []
    seen = set()
    for q in merged:
        q2 = q.strip()
        if not q2.endswith('?'):
            continue
        if q2 not in seen:
            seen.add(q2)
            cleaned.append(q2)

    if not cleaned:
        return [
            "Je maumivu yalianza lini?",
            "Je maumivu ni makali kiasi gani (1-10)?",
            "Je una dalili nyingine kama homa, kutapika, au kuharisha?",
        ]

    return cleaned[:6]
