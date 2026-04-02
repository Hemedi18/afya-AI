import base64
from io import BytesIO
import json
from urllib.parse import quote
from collections import Counter

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import HealthCardForm, PersonaReminderConfigForm
from .models import CardNotification, HealthCard, PersonaReminderConfig, ensure_persona_update_notification
from menstrual.models import DailyLog

try:
	import qrcode
except Exception:  # pragma: no cover
	qrcode = None


def _build_qr_image_data_uri(data: str) -> str:
	if qrcode is None:
		return f"https://api.qrserver.com/v1/create-qr-code/?size=260x260&data={quote(data)}"
	qr = qrcode.QRCode(version=1, box_size=8, border=2)
	qr.add_data(data)
	qr.make(fit=True)
	img = qr.make_image(fill_color='black', back_color='white')
	buffer = BytesIO()
	img.save(buffer, format='PNG')
	encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
	return f"data:image/png;base64,{encoded}"


def _build_selected_health_data(card: HealthCard):
	persona = getattr(card.user, 'ai_persona', None)
	logs_qs = DailyLog.objects.filter(cycle__user=card.user).order_by('-date')
	recent_logs = list(logs_qs[:30])

	selected = {
		'basic_identity': {},
		'persona_health': {},
		'menstrual': {},
		'ai_summary': None,
	}

	if card.show_name:
		selected['basic_identity']['full_name'] = card.display_name
	if card.show_gender:
		selected['basic_identity']['gender'] = card.display_gender
	if card.show_birth_date and card.birth_date:
		selected['basic_identity']['birth_date'] = card.birth_date.isoformat()
	if card.show_age and card.display_age is not None:
		selected['basic_identity']['age'] = card.display_age

	if persona:
		if card.show_health_notes:
			selected['persona_health']['health_notes'] = persona.health_notes.strip() or 'No health notes provided.'
		if card.show_permanent_diseases:
			selected['persona_health']['permanent_diseases'] = persona.permanent_diseases.strip() or 'No permanent diseases reported.'
		if card.show_medications:
			selected['persona_health']['medications'] = persona.medications.strip() or 'No medications.'
		if card.show_goals:
			selected['persona_health']['goals'] = persona.goals.strip() or 'No health goals specified.'
		if card.show_lifestyle:
			selected['persona_health']['lifestyle_notes'] = persona.lifestyle_notes.strip() or 'No lifestyle notes provided.'
	else:
		if card.show_health_notes:
			selected['persona_health']['health_notes'] = 'No health notes provided.'
		if card.show_permanent_diseases:
			selected['persona_health']['permanent_diseases'] = 'No permanent diseases reported.'
		if card.show_medications:
			selected['persona_health']['medications'] = 'No medications.'
		if card.show_goals:
			selected['persona_health']['goals'] = 'No health goals specified.'
		if card.show_lifestyle:
			selected['persona_health']['lifestyle_notes'] = 'No lifestyle notes provided.'

	if card.show_menstrual_logs and recent_logs:
		selected['menstrual']['recent_logs'] = [
			{
				'date': log.date.isoformat(),
				'flow_intensity': int(log.flow_intensity or 0),
				'physical_symptoms': log.physical_symptoms or [],
				'emotional_changes': log.emotional_changes or [],
				'sleep_patterns': log.sleep_patterns or [],
				'ai_suggestion': log.ai_suggestion or '',
			}
			for log in recent_logs
		]

	if (card.show_menstrual_chart or card.show_ai_summary) and recent_logs:
		chronological = list(reversed(recent_logs))
		flow_values = [int(log.flow_intensity or 0) for log in chronological]
		labels = [log.date.strftime('%d %b') for log in chronological]
		all_symptoms = []
		for log in recent_logs:
			for item in (log.physical_symptoms or []):
				if isinstance(item, str) and item.strip():
					all_symptoms.append(item.strip())
		top_symptoms = [name for name, _ in Counter(all_symptoms).most_common(5)]
		avg_flow = round(sum(flow_values) / len(flow_values), 2) if flow_values else 0

		if card.show_menstrual_chart:
			selected['menstrual']['chart'] = {
				'labels': labels,
				'flow': flow_values,
			}

		if card.show_ai_summary:
			selected['ai_summary'] = {
				'title': 'AI Health Summary',
				'text': (
					f"Kwa logs {len(recent_logs)} za karibuni, wastani wa flow ni {avg_flow}/5. "
					f"Dalili zinazoonekana zaidi: {', '.join(top_symptoms) if top_symptoms else 'hakuna data ya kutosha'}."
				),
				'avg_flow': avg_flow,
				'top_symptoms': top_symptoms,
				'logs_count': len(recent_logs),
			}

	return selected


@login_required
def card_home(request):
	card, _ = HealthCard.objects.get_or_create(user=request.user)
	config, _ = PersonaReminderConfig.objects.get_or_create(user=request.user)

	ensure_persona_update_notification(request.user)

	public_url = request.build_absolute_uri(reverse('card:public_profile', kwargs={'token': str(card.public_token)}))
	qr_image = _build_qr_image_data_uri(public_url)
	unread_notifications = CardNotification.objects.filter(user=request.user, is_read=False)[:5]

	return render(request, 'card/home.html', {
		'card_obj': card,
		'public_url': public_url,
		'qr_image': qr_image,
		'unread_notifications': unread_notifications,
		'persona_config': config,
	})


@login_required
def card_details(request):
	card, _ = HealthCard.objects.get_or_create(user=request.user)
	config, _ = PersonaReminderConfig.objects.get_or_create(user=request.user)

	if request.method == 'POST':
		form = HealthCardForm(request.POST, request.FILES, instance=card)
		config_form = PersonaReminderConfigForm(request.POST, instance=config)
		if form.is_valid() and config_form.is_valid():
			card_obj = form.save(commit=False)
			new_pwd = (form.cleaned_data.get('public_password') or '').strip()
			clear_pwd = form.cleaned_data.get('clear_public_password')
			if clear_pwd:
				card_obj.clear_public_password()
			elif new_pwd:
				card_obj.set_public_password(new_pwd)
			card_obj.save()
			config_form.save()
			CardNotification.objects.create(
				user=request.user,
				kind=CardNotification.KIND_CARD_UPDATED,
				title='Card details zimesasishwa',
				body='Muonekano wa card na taarifa za scan zimehifadhiwa kwa mafanikio.',
			)
			messages.success(request, 'Card details zimesasishwa.')
			return redirect('card:details')
	else:
		form = HealthCardForm(instance=card)
		config_form = PersonaReminderConfigForm(instance=config)

	return render(request, 'card/details.html', {
		'form': form,
		'config_form': config_form,
		'card_obj': card,
	})


@login_required
def card_notifications(request):
	notifications = CardNotification.objects.filter(user=request.user)
	if request.method == 'POST':
		notifications.filter(is_read=False).update(is_read=True)
		messages.success(request, 'Notifications zimewekwa kama zimesomwa.')
		return redirect('card:notifications')
	return render(request, 'card/notifications.html', {'notifications': notifications})


def public_profile(request, token):
	card = get_object_or_404(HealthCard, public_token=token)
	session_key = f'card_access_{card.public_token}'

	if card.requires_public_password and not request.session.get(session_key):
		if request.method == 'POST':
			password = (request.POST.get('access_password') or '').strip()
			if card.check_public_password(password):
				request.session[session_key] = True
				return redirect('card:public_profile', token=card.public_token)
			return render(request, 'card/public_profile.html', {
				'locked': True,
				'owner': card.user,
				'generated_at': timezone.now(),
				'access_error': 'Password si sahihi. Jaribu tena.',
			})
		return render(request, 'card/public_profile.html', {
			'locked': True,
			'owner': card.user,
			'generated_at': timezone.now(),
		})

	selected_data = _build_selected_health_data(card)
	payload = {
		'meta': {
			'username': card.user.username,
			'generated_at': timezone.now().isoformat(),
			'card_updated_at': card.updated_at.isoformat(),
		},
		'selected_data': selected_data,
	}
	if request.headers.get('accept', '').lower().find('application/json') >= 0 or request.GET.get('format') == 'json':
		return JsonResponse(payload)
	return render(request, 'card/public_profile.html', {
		'payload': payload,
		'selected_data': selected_data,
		'chart_json': json.dumps((selected_data.get('menstrual') or {}).get('chart') or {'labels': [], 'flow': []}),
		'owner': card.user,
		'generated_at': timezone.now(),
		'payload_pretty': json.dumps(payload, indent=2, ensure_ascii=False),
	})
