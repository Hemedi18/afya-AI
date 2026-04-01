import json
import logging
import requests
from xml.sax.saxutils import escape

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from AI_brain.services import ask_ai_brain

from .models import OfflineConversation, OfflineMessage, SmsWebhookLog
from .services import generate_offline_ai_reply, send_africastalking_sms


logger = logging.getLogger(__name__)


def _twiml_message(message_text: str) -> str:
	text = escape(message_text or '')
	return f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{text}</Message></Response>'


@csrf_exempt
def sms_webhook(request):
	"""
	Africa's Talking SMS webhook endpoint.
	Receives inbound SMS and sends outbound SMS reply.
	"""
	if request.method != 'POST':
		return HttpResponse('Method Not Allowed', status=405)

	payload = {}
	if request.content_type and 'application/json' in request.content_type:
		try:
			payload = json.loads((request.body or b'{}').decode('utf-8'))
		except Exception:
			payload = {}
	else:
		payload = {k: v for k, v in request.POST.items()}

	message_obj = payload.get('message') or {}
	if isinstance(message_obj, dict):
		inbound_text = message_obj.get('text', '')
	else:
		inbound_text = ''

	sender = (
		str(payload.get('from') or payload.get('phoneNumber') or payload.get('msisdn') or '')
	).strip()
	message_text = (
		str(payload.get('text') or payload.get('message') or inbound_text or '')
	).strip()
	if not message_text:
		reply_text = 'Ujumbe wako uko tupu. Tafadhali tuma swali lako tena.'
	else:
		reply_text = ask_ai_brain(message_text)

	sent_ok = False
	send_detail = 'No sender number provided.'
	if sender:
		sent_ok, send_detail = send_africastalking_sms(sender, reply_text)

	try:
		SmsWebhookLog.objects.create(
			sender=sender,
			message_text=message_text,
			reply_text=reply_text,
			outbound_sent=sent_ok,
			outbound_detail=send_detail,
			raw_payload=payload,
		)
	except Exception:
		logger.exception('Failed to save SmsWebhookLog')

	logger.info(
		'SMS webhook: from=%s text=%s reply=%s outbound_ok=%s detail=%s',
		sender,
		message_text[:120],
		reply_text[:120],
		sent_ok,
		send_detail[:200],
	)

	return HttpResponse(reply_text, content_type='text/plain; charset=utf-8')


@csrf_exempt
def twilio_sms_webhook(request):
	"""
	Twilio SMS webhook endpoint.
	Twilio sends form-encoded fields like `From` and `Body`.
	The AI reply is returned as TwiML so Twilio sends it back to the user.
	"""
	if request.method != 'POST':
		return HttpResponse('Method Not Allowed', status=405)

	payload = {k: v for k, v in request.POST.items()}
	sender = (request.POST.get('From') or request.POST.get('WaId') or '').strip()
	message_text = (request.POST.get('Body') or '').strip()

	if not message_text:
		reply_text = 'Ujumbe wako uko tupu. Tafadhali tuma swali lako tena.'
	else:
		reply_text = ask_ai_brain(message_text)

	try:
		SmsWebhookLog.objects.create(
			sender=sender,
			message_text=message_text,
			reply_text=reply_text,
			outbound_sent=True,
			outbound_detail='Twilio TwiML response prepared.',
			raw_payload=payload,
		)
	except Exception:
		logger.exception('Failed to save SmsWebhookLog (twilio_sms_webhook)')

	logger.info(
		'Twilio SMS webhook: from=%s text=%s reply=%s',
		sender,
		message_text[:120],
		reply_text[:120],
	)

	return HttpResponse(_twiml_message(reply_text), content_type='application/xml; charset=utf-8')


@csrf_exempt
def android_sms_webhook(request):
	"""
	Android SMS Gateway webhook endpoint.
	Receives POST {phone, message}, generates AI response, then posts back to
	the Android SMS Gateway send API using requests.
	"""
	if request.method != 'POST':
		return JsonResponse({'ok': False, 'error': 'Method Not Allowed'}, status=405)

	payload = {}
	if request.content_type and 'application/json' in request.content_type:
		try:
			payload = json.loads((request.body or b'{}').decode('utf-8'))
		except Exception:
			payload = {}
	else:
		payload = {k: v for k, v in request.POST.items()}

	phone = str(payload.get('phone') or payload.get('from') or '').strip()
	message_text = str(payload.get('message') or payload.get('text') or '').strip()

	if not phone:
		return JsonResponse({'ok': False, 'error': 'Missing phone'}, status=400)
	if not message_text:
		return JsonResponse({'ok': False, 'error': 'Missing message'}, status=400)

	reply_text = ask_ai_brain(message_text)

	send_url = getattr(settings, 'ANDROID_SMS_GATEWAY_SEND_URL', '')
	token = getattr(settings, 'ANDROID_SMS_GATEWAY_TOKEN', '')

	sent_ok = False
	send_detail = 'ANDROID_SMS_GATEWAY_SEND_URL not configured.'

	if send_url:
		headers = {'Content-Type': 'application/json'}
		if token:
			headers['Authorization'] = f'Bearer {token}'

		out_payload = {
			'phone': phone,
			'message': reply_text,
		}

		try:
			res = requests.post(send_url, json=out_payload, headers=headers, timeout=20)
			if 200 <= res.status_code < 300:
				sent_ok = True
				send_detail = (res.text or 'OK')[:240]
			else:
				send_detail = f'HTTP {res.status_code}: {(res.text or "")[:240]}'
		except Exception as exc:
			send_detail = str(exc)

	try:
		SmsWebhookLog.objects.create(
			sender=phone,
			message_text=message_text,
			reply_text=reply_text,
			outbound_sent=sent_ok,
			outbound_detail=send_detail,
			raw_payload=payload,
		)
	except Exception:
		logger.exception('Failed to save SmsWebhookLog (android_sms_webhook)')

	logger.info(
		'Android SMS webhook: phone=%s text=%s reply=%s outbound_ok=%s detail=%s',
		phone,
		message_text[:120],
		reply_text[:120],
		sent_ok,
		send_detail[:200],
	)

	return JsonResponse(
		{
			'ok': True,
			'phone': phone,
			'outbound_sent': sent_ok,
			'detail': send_detail,
		}
	)


class OfflineChatPageView(LoginRequiredMixin, View):
	template_name = 'offline_chat/chat.html'

	def get(self, request, *args, **kwargs):
		conversations = OfflineConversation.objects.filter(user=request.user).prefetch_related('messages')
		active_id = request.GET.get('c')
		if active_id:
			active_conversation = get_object_or_404(conversations, pk=active_id)
		else:
			active_conversation = conversations.first()

		context = {
			'conversations': conversations[:30],
			'active_conversation': active_conversation,
			'active_messages': active_conversation.messages.all()[:80] if active_conversation else [],
		}
		return render(request, self.template_name, context)


class OfflineConversationCreateView(LoginRequiredMixin, View):
	def post(self, request, *args, **kwargs):
		convo = OfflineConversation.objects.create(
			user=request.user,
			title='Mazungumzo mapya',
		)
		return JsonResponse({'ok': True, 'conversation_id': convo.id})


class OfflineChatSendView(LoginRequiredMixin, View):
	def post(self, request, *args, **kwargs):
		try:
			payload = json.loads(request.body.decode('utf-8'))
		except Exception:
			payload = request.POST

		message = (payload.get('message') or '').strip()
		conversation_id = payload.get('conversation_id')

		if not message:
			return JsonResponse({'ok': False, 'error': 'Ujumbe hauwezi kuwa tupu.'}, status=400)

		if conversation_id:
			conversation = get_object_or_404(OfflineConversation, pk=conversation_id, user=request.user)
		else:
			conversation = OfflineConversation.objects.create(user=request.user, title='Mazungumzo mapya')

		OfflineMessage.objects.create(
			conversation=conversation,
			role=OfflineMessage.ROLE_USER,
			content=message,
		)

		history = [
			{'role': m.role, 'content': m.content}
			for m in conversation.messages.exclude(role=OfflineMessage.ROLE_SYSTEM).order_by('-created_at')[:12][::-1]
		]

		reply, model_name = generate_offline_ai_reply(history, message)

		OfflineMessage.objects.create(
			conversation=conversation,
			role=OfflineMessage.ROLE_ASSISTANT,
			content=reply,
		)

		if conversation.title in {'', 'Mazungumzo mapya'}:
			conversation.title = (message[:55] + '...') if len(message) > 55 else message
		conversation.model_name = model_name
		conversation.save(update_fields=['title', 'model_name', 'updated_at'])

		return JsonResponse(
			{
				'ok': True,
				'conversation_id': conversation.id,
				'reply': reply,
				'conversation_title': conversation.title,
				'model': model_name,
			}
		)
