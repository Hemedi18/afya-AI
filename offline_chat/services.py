from django.conf import settings
import httpx


def _fallback_reply(user_message: str) -> str:
    text = (user_message or '').strip()
    if not text:
        return 'Naomba andika swali lako kwanza.'
    return (
        'Nimepokea swali lako. Kwa sasa offline AI haijapatikana, lakini hapa kuna mwongozo wa haraka: '\
        'andika dalili kuu, muda ulioanza, na ukali wake ili nipate kukusaidia vizuri zaidi.'
    )


def generate_offline_ai_reply(conversation_messages, user_message: str) -> tuple[str, str]:
    """
    Returns (reply_text, model_name_used).
    Uses local Ollama server. Falls back gracefully when server/model is unavailable.
    """
    model_name = getattr(settings, 'OLLAMA_MODEL', 'llama3.2:3b')
    host = getattr(settings, 'OLLAMA_HOST', 'http://127.0.0.1:11434')

    try:
        from ollama import Client

        client = Client(host=host)
        messages = [
            {
                'role': 'system',
                'content': (
                    'You are a safe, concise reproductive-health assistant. '
                    'Respond in clear Swahili unless user asks otherwise. '
                    'Do not provide dangerous instructions. '
                    'If emergency red flags appear, advise immediate clinic/hospital care.'
                ),
            }
        ]
        messages.extend(conversation_messages)
        messages.append({'role': 'user', 'content': user_message})

        result = client.chat(
            model=model_name,
            messages=messages,
            options={'temperature': 0.4},
        )
        content = (result.get('message') or {}).get('content') or ''
        content = content.strip()
        if not content:
            return _fallback_reply(user_message), model_name
        return content, model_name
    except Exception:
        return _fallback_reply(user_message), model_name


def _normalize_msisdn(number: str) -> str:
    return (number or '').strip().replace('+', '').replace(' ', '')


def send_africastalking_sms(to_number: str, message_text: str) -> tuple[bool, str]:
    """
    Sends SMS via Africa's Talking REST API.
    Returns (ok, detail_message).
    """
    username = getattr(settings, 'AT_USERNAME', '')
    api_key = getattr(settings, 'AT_API_KEY', '')
    auth_token = getattr(settings, 'AT_AUTH_TOKEN', '')
    sender_id = getattr(settings, 'AT_SENDER_ID', '')
    env = (getattr(settings, 'AT_ENV', 'sandbox') or 'sandbox').lower()

    if not api_key and not auth_token:
        return False, 'AT credentials missing (AT_API_KEY or AT_AUTH_TOKEN).'
    if not username and not auth_token:
        return False, 'AT username missing (AT_USERNAME).'

    base_url = 'https://api.sandbox.africastalking.com' if env == 'sandbox' else 'https://api.africastalking.com'
    send_url = f'{base_url}/version1/messaging'

    msisdn = _normalize_msisdn(to_number)
    if not msisdn:
        return False, 'Destination number is missing.'

    payload = {
        'to': msisdn,
        'message': message_text,
    }
    if username:
        payload['username'] = username
    if sender_id:
        payload['from'] = sender_id

    headers = {
        'Accept': 'application/json',
    }
    if auth_token:
        headers['authToken'] = auth_token
    else:
        headers['apiKey'] = api_key

    try:
        res = httpx.post(
            send_url,
            data=payload,
            headers=headers,
            timeout=20,
        )
        if 200 <= res.status_code < 300:
            return True, res.text[:240]
        mode = 'authToken' if auth_token else 'apiKey'
        return False, f'HTTP {res.status_code} ({mode}): {res.text[:240]}'
    except Exception as exc:
        return False, str(exc)


def send_twilio_sms(to_number: str, message_text: str) -> tuple[bool, str]:
    """
    Sends SMS via Twilio REST API.
    Returns (ok, detail_message).
    """
    account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
    auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
    phone_number = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
    messaging_service_sid = getattr(settings, 'TWILIO_MESSAGING_SERVICE_SID', '')

    if not account_sid or not auth_token:
        return False, 'Twilio credentials missing (TWILIO_ACCOUNT_SID/TWILIO_AUTH_TOKEN).'

    msisdn = (to_number or '').strip()
    if not msisdn:
        return False, 'Destination number is missing.'

    url = f'https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json'
    data = {
        'To': msisdn,
        'Body': message_text,
    }
    if messaging_service_sid:
        data['MessagingServiceSid'] = messaging_service_sid
    elif phone_number:
        data['From'] = phone_number
    else:
        return False, 'Twilio sender missing (TWILIO_PHONE_NUMBER or TWILIO_MESSAGING_SERVICE_SID).'

    try:
        res = httpx.post(
            url,
            data=data,
            auth=(account_sid, auth_token),
            headers={'Accept': 'application/json'},
            timeout=20,
        )
        if 200 <= res.status_code < 300:
            return True, res.text[:240]
        return False, f'HTTP {res.status_code}: {res.text[:240]}'
    except Exception as exc:
        return False, str(exc)
