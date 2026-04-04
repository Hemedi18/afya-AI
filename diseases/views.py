import json
import os

import requests
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import get_language, gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Disease


def _json_body(request):
	try:
		return json.loads(request.body.decode('utf-8') or '{}')
	except (json.JSONDecodeError, UnicodeDecodeError):
		return {}


class WHOClient:
	token_url = 'https://icdaccessmanagement.who.int/connect/token'
	base_url = 'https://id.who.int/icd/entity'

	def __init__(self):
		self.client_id = (os.getenv('CLIENT_ID') or '').strip()
		self.client_secret = (os.getenv('CLIENT_SECRET') or '').strip()

	def _token(self):
		if not self.client_id or not self.client_secret:
			return None
		payload = {
			'client_id': self.client_id,
			'client_secret': self.client_secret,
			'grant_type': 'client_credentials',
			'scope': 'icdapi_access',
		}
		try:
			res = requests.post(self.token_url, data=payload, timeout=10)
			res.raise_for_status()
			return (res.json() or {}).get('access_token')
		except Exception:
			return None

	def _headers(self, token, lang='en'):
		return {
			'Authorization': f'Bearer {token}',
			'API-Version': 'v2',
			'Accept-Language': lang or 'en',
		}

	def search(self, query, lang='en', limit=10):
		token = self._token()
		if not token or not query:
			return []
		params = {'q': query, 'useFlexisearch': 'true'}
		try:
			res = requests.get(
				f'{self.base_url}/search',
				headers=self._headers(token, lang=lang),
				params=params,
				timeout=10,
			)
			res.raise_for_status()
			entities = (res.json() or {}).get('destinationEntities') or []
		except Exception:
			return []

		out = []
		for item in entities[: max(1, min(int(limit or 10), 20))]:
			out.append(
				{
					'id_url': item.get('id', ''),
					'title': item.get('title', ''),
					'source': 'who_icd',
				}
			)
		return out

	def detail_by_query(self, query, lang='en'):
		matches = self.search(query, lang=lang, limit=1)
		if not matches:
			return None

		token = self._token()
		if not token:
			return None

		entity_url = matches[0].get('id_url')
		if not entity_url:
			return None

		try:
			res = requests.get(entity_url, headers=self._headers(token, lang=lang), timeout=10)
			res.raise_for_status()
			details = res.json() or {}
		except Exception:
			return None

		return {
			'source': 'who_icd',
			'query': query,
			'title': (details.get('title') or {}).get('@value') or matches[0].get('title', ''),
			'definition': (details.get('definition') or {}).get('@value', ''),
			'id_url': entity_url,
		}


def disease_browser(request):
	q = (request.GET.get('q') or '').strip()
	active_lang = (get_language() or 'en').split('-')[0]
	lang = (request.GET.get('lang') or active_lang or 'en').strip().lower()
	if lang not in {'en', 'sw', 'ar'}:
		lang = 'en'

	local_qs = Disease.objects.all()
	if q:
		local_qs = local_qs.filter(
			Q(name__icontains=q)
			| Q(icd_code__icontains=q)
			| Q(definition__icontains=q)
			| Q(symptoms__icontains=q)
			| Q(prevention__icontains=q)
			| Q(treatment__icontains=q)
		)

	local_items = list(local_qs[:12])
	who_item = WHOClient().detail_by_query(q, lang=lang) if q else None

	return render(
		request,
		'diseases/index.html',
		{
			'query': q,
			'lang_choice': lang,
			'site_lang': active_lang,
			'local_items': local_items,
			'who_item': who_item,
			'results_count': len(local_items) + (1 if who_item else 0),
		},
	)


def disease_detail(request, disease_id):
	item = get_object_or_404(Disease, pk=disease_id)
	return render(request, 'diseases/detail.html', {'item': item})


@method_decorator(csrf_exempt, name='dispatch')
class DiseaseListCreateApiView(View):
	def get(self, request, *args, **kwargs):
		q = (request.GET.get('q') or '').strip()
		qs = Disease.objects.all()
		if q:
			qs = qs.filter(
				Q(name__icontains=q)
				| Q(icd_code__icontains=q)
				| Q(definition__icontains=q)
				| Q(symptoms__icontains=q)
			)
		return JsonResponse({'ok': True, 'items': [d.to_dict() for d in qs[:100]]})

	def post(self, request, *args, **kwargs):
		data = _json_body(request)
		name = (data.get('name') or '').strip()
		if not name:
			return JsonResponse({'ok': False, 'error': _('name is required')}, status=400)

		obj = Disease.objects.create(
			name=name,
			icd_code=(data.get('icd_code') or '').strip(),
			definition=(data.get('definition') or '').strip(),
			symptoms=(data.get('symptoms') or '').strip(),
			prevention=(data.get('prevention') or '').strip(),
			treatment=(data.get('treatment') or '').strip(),
		)
		return JsonResponse({'ok': True, 'item': obj.to_dict()}, status=201)


class DiseaseDetailApiView(View):
	def get(self, request, disease_id, *args, **kwargs):
		obj = get_object_or_404(Disease, pk=disease_id)
		return JsonResponse({'ok': True, 'item': obj.to_dict()})


class DiseaseWhoSearchApiView(View):
	def get(self, request, *args, **kwargs):
		q = (request.GET.get('q') or '').strip()
		active_lang = (get_language() or 'en').split('-')[0]
		lang = (request.GET.get('lang') or active_lang or 'en').strip().lower()
		if lang not in {'en', 'sw', 'ar'}:
			lang = 'en'
		if not q:
			return JsonResponse({'ok': False, 'error': _('q is required')}, status=400)

		client = WHOClient()
		items = client.search(q, lang=lang)
		return JsonResponse({'ok': True, 'query': q, 'items': items})


class DiseaseWhoDetailApiView(View):
	def get(self, request, *args, **kwargs):
		q = (request.GET.get('q') or '').strip()
		active_lang = (get_language() or 'en').split('-')[0]
		lang = (request.GET.get('lang') or active_lang or 'en').strip().lower()
		if lang not in {'en', 'sw', 'ar'}:
			lang = 'en'
		if not q:
			return JsonResponse({'ok': False, 'error': _('q is required')}, status=400)

		client = WHOClient()
		item = client.detail_by_query(q, lang=lang)
		if not item:
			return JsonResponse({'ok': False, 'error': _('No WHO result found or WHO auth not configured')}, status=404)

		return JsonResponse({'ok': True, 'item': item})
