import json

import requests
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Medication


def _json_body(request):
	try:
		return json.loads(request.body.decode('utf-8') or '{}')
	except (json.JSONDecodeError, UnicodeDecodeError):
		return {}


def _fetch_openfda_medications(query, limit=5):
	if not query:
		return []

	url = 'https://api.fda.gov/drug/label.json'
	params = {
		'search': f'openfda.brand_name:"{query}"+openfda.generic_name:"{query}"',
		'limit': max(1, min(int(limit or 5), 20)),
	}
	try:
		response = requests.get(url, params=params, timeout=10)
		response.raise_for_status()
		payload = response.json()
	except Exception:
		return []

	out = []
	for item in payload.get('results', []):
		openfda = item.get('openfda', {}) or {}
		out.append(
			{
				'source': 'openfda',
				'name': (openfda.get('brand_name') or [''])[0],
				'generic_name': (openfda.get('generic_name') or [''])[0],
				'manufacturer': (openfda.get('manufacturer_name') or [''])[0],
				'dosage': (item.get('dosage_and_administration') or [''])[0],
				'description': (item.get('indications_and_usage') or [''])[0],
				'active_ingredients': ', '.join(openfda.get('substance_name') or []),
				'rx_required': any(code == 'Rx' for code in (openfda.get('product_type') or [])),
			}
		)
	return out


def medication_browser(request):
	q = (request.GET.get('q') or '').strip()
	include_remote = (request.GET.get('include_remote') or '1').strip().lower() in {'1', 'true', 'yes'}

	local_qs = Medication.objects.all()
	if q:
		local_qs = local_qs.filter(
			Q(name__icontains=q)
			| Q(generic_name__icontains=q)
			| Q(active_ingredients__icontains=q)
			| Q(manufacturer__icontains=q)
			| Q(description__icontains=q)
		)

	local_items = list(local_qs[:12])
	remote_items = _fetch_openfda_medications(q, limit=6) if (q and include_remote) else []

	return render(
		request,
		'medics/index.html',
		{
			'query': q,
			'include_remote': include_remote,
			'local_items': local_items,
			'remote_items': remote_items,
			'results_count': len(local_items) + len(remote_items),
		},
	)


def medication_detail(request, medication_id):
	item = get_object_or_404(Medication, pk=medication_id)
	return render(request, 'medics/detail.html', {'item': item})


@method_decorator(csrf_exempt, name='dispatch')
class MedicationListCreateApiView(View):
	def get(self, request, *args, **kwargs):
		q = (request.GET.get('q') or '').strip()
		include_remote = (request.GET.get('include_remote') or '').strip().lower() in {'1', 'true', 'yes'}
		limit = request.GET.get('limit', '20')
		try:
			limit = max(1, min(int(limit), 100))
		except ValueError:
			limit = 20

		qs = Medication.objects.all()
		if q:
			qs = qs.filter(
				Q(name__icontains=q)
				| Q(generic_name__icontains=q)
				| Q(active_ingredients__icontains=q)
				| Q(manufacturer__icontains=q)
			)
		local_items = [m.to_dict() for m in qs[:limit]]

		remote_items = _fetch_openfda_medications(q, limit=min(limit, 10)) if include_remote else []
		return JsonResponse(
			{
				'ok': True,
				'query': q,
				'count_local': len(local_items),
				'count_remote': len(remote_items),
				'items': local_items,
				'remote_items': remote_items,
			}
		)

	def post(self, request, *args, **kwargs):
		data = _json_body(request)
		name = (data.get('name') or '').strip()
		if not name:
			return JsonResponse({'ok': False, 'error': _('name is required')}, status=400)

		obj = Medication.objects.create(
			name=name,
			generic_name=(data.get('generic_name') or '').strip(),
			description=(data.get('description') or '').strip(),
			dosage=(data.get('dosage') or '').strip(),
			manufacturer=(data.get('manufacturer') or '').strip(),
			active_ingredients=(data.get('active_ingredients') or '').strip(),
			rx_required=bool(data.get('rx_required', False)),
		)
		return JsonResponse({'ok': True, 'item': obj.to_dict()}, status=201)


class MedicationDetailApiView(View):
	def get(self, request, medication_id, *args, **kwargs):
		obj = get_object_or_404(Medication, pk=medication_id)
		return JsonResponse({'ok': True, 'item': obj.to_dict()})
