import base64
from io import BytesIO
import json
from urllib.parse import quote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import HealthCardForm, PersonaReminderConfigForm
from .models import CardNotification, HealthCard, PersonaReminderConfig, ensure_persona_update_notification

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
			form.save()
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
	payload = card.build_public_payload()
	if request.headers.get('accept', '').lower().find('application/json') >= 0 or request.GET.get('format') == 'json':
		return JsonResponse(payload)
	return render(request, 'card/public_profile.html', {
		'payload': payload,
		'owner': card.user,
		'generated_at': timezone.now(),
		'payload_pretty': json.dumps(payload, indent=2, ensure_ascii=False),
	})
