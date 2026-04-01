from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.utils import timezone
from collections import Counter

from .services import generate_ai_text
from users.models import UserAIPersona
from menstrual.models import DailyLog
from .models import AIInteractionLog


def _build_persona_prompt_block(persona):
	if not persona:
		return ""

	parts = []
	if persona.age:
		parts.append(f"Age: {persona.age}")
	if persona.gender:
		parts.append(f"Gender: {persona.gender}")
	if persona.height_cm:
		parts.append(f"Height: {persona.height_cm} cm")
	if persona.weight_kg:
		parts.append(f"Weight: {persona.weight_kg} kg")
	if persona.health_notes:
		parts.append(f"Health: {persona.health_notes}")
	if persona.permanent_diseases:
		parts.append(f"Permanent diseases: {persona.permanent_diseases}")
	if persona.medications:
		parts.append(f"Medication: {persona.medications}")
	if persona.lifestyle_notes:
		parts.append(f"Lifestyle: {persona.lifestyle_notes}")
	if persona.sleep_hours:
		parts.append(f"Sleep: {persona.sleep_hours} hours")
	if persona.stress_level:
		parts.append(f"Stress: {persona.stress_level}")
	if persona.exercise_frequency:
		parts.append(f"Exercise: {persona.exercise_frequency}")
	if persona.diet:
		parts.append(f"Diet (optional): {persona.diet}")
	if persona.goals:
		parts.append(f"Goals (optional): {persona.goals}")
	if persona.mental_health:
		parts.append(f"Mental health (optional): {persona.mental_health}")

	if not parts:
		return ""

	joined = "\n- ".join(parts)
	return (
		"Personalization profile ya mtumiaji (tumia hii kutoa jibu personalized, salama, lisilo na panic):\n"
		f"- {joined}\n\n"
	)


def _build_recent_health_signal_block(user):
	window_start = timezone.now().date() - timezone.timedelta(days=30)
	logs = list(
		DailyLog.objects.filter(cycle__user=user, date__gte=window_start)
		.order_by('-date')[:60]
	)
	if not logs:
		return "", {'logs_30d': 0}

	flow_values = [int(log.flow_intensity or 0) for log in logs if log.flow_intensity is not None]
	avg_flow = round(sum(flow_values) / len(flow_values), 2) if flow_values else 0

	all_symptoms = []
	for log in logs:
		for item in (log.physical_symptoms or []):
			if isinstance(item, str) and item.strip():
				all_symptoms.append(item.strip().lower())

	top_symptoms = [name for name, _ in Counter(all_symptoms).most_common(5)]
	latest_log_date = logs[0].date.isoformat() if logs else None

	lines = [
		f"Recent logs (last 30 days): {len(logs)}",
		f"Average flow intensity: {avg_flow}/5" if flow_values else "Average flow intensity: no data",
		f"Top physical symptoms: {', '.join(top_symptoms)}" if top_symptoms else "Top physical symptoms: no data",
		f"Most recent log date: {latest_log_date}" if latest_log_date else "",
	]
	joined = "\n- ".join([line for line in lines if line])
	block = f"Signals kutoka cycle logs:\n- {joined}\n\n"

	return block, {
		'logs_30d': len(logs),
		'avg_flow': avg_flow,
		'top_symptoms': top_symptoms,
		'latest_log_date': latest_log_date,
	}


def _build_quality_rules_block(persona):
	rules = [
		f"AI data consent: {'yes' if persona.ai_data_consent else 'no'}",
		f"Profile completeness score: {persona.profile_completeness_score}%",
		f"Identity verified: {'yes' if persona.identity_verified else 'no'}",
		f"Medical info verified: {'yes' if persona.medical_info_verified else 'no'}",
	]
	if not persona.ai_data_consent:
		rules.append("Usitoe personalization ya kina; toa mwongozo wa general safety tu.")
	if persona.profile_completeness_score < 60:
		rules.append("Onyesha confidence ni ndogo kwa sababu data profile bado haijakamilika.")
	if not persona.identity_verified or not persona.medical_info_verified:
		rules.append("Taja kuwa mapendekezo yanategemea self-reported data, si verified clinical record.")
	joined = "\n- ".join(rules)
	return f"Quality & verification rules:\n- {joined}\n\n"


def _store_ai_log(user, question, reply, persona, context_payload):
	AIInteractionLog.objects.create(
		user=user,
		question=question,
		reply=reply or '',
		persona_completeness=persona.profile_completeness_score,
		identity_verified=persona.identity_verified,
		medical_info_verified=persona.medical_info_verified,
		context_payload=context_payload,
	)


class AIChatView(LoginRequiredMixin, View):
	template_name = 'AI_brain/ai_chat.html'

	def get(self, request, *args, **kwargs):
		persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
		persona.update_quality_metrics(save=True)
		return render(
			request,
			self.template_name,
			{
				'reply': None,
				'question': '',
				'onboarding_complete': persona.onboarding_complete,
			},
		)

	def post(self, request, *args, **kwargs):
		question = (request.POST.get('question') or '').strip()
		persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
		persona.update_quality_metrics(save=True)

		reply = None
		if question:
			fallback = (
				"Asante kwa swali lako. Kwa sasa AI haijapatikana. "
				"Kwa usalama wako, endelea kufuatilia dalili na wasiliana na daktari endapo maumivu ni makali."
			)
			signal_block, signal_payload = _build_recent_health_signal_block(request.user)
			prompt = (
				_build_quality_rules_block(persona)
				+ _build_persona_prompt_block(persona)
				+ signal_block
				+ f"Swali la mtumiaji: {question}"
			)
			reply = generate_ai_text(prompt, fallback)
			_store_ai_log(
				request.user,
				question,
				reply,
				persona,
				{
					'quality_label': persona.data_quality_label,
					'completeness': persona.profile_completeness_score,
					'identity_verified': persona.identity_verified,
					'medical_info_verified': persona.medical_info_verified,
					'signal': signal_payload,
				},
			)

		return render(
			request,
			self.template_name,
			{
				'reply': reply,
				'question': question,
				'onboarding_complete': persona.onboarding_complete,
			},
		)


class AIQuickChatView(LoginRequiredMixin, View):
	def post(self, request, *args, **kwargs):
		question = (request.POST.get('question') or '').strip()
		if not question:
			return JsonResponse({'ok': False, 'error': 'Tafadhali andika swali.'}, status=400)

		persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
		persona.update_quality_metrics(save=True)
		fallback = (
			"Samahani, kwa sasa AI haijapatikana. "
			"Kwa usalama wako, fuatilia dalili zako na wasiliana na daktari kama maumivu ni makali."
		)
		signal_block, signal_payload = _build_recent_health_signal_block(request.user)
		prompt = (
			_build_quality_rules_block(persona)
			+ _build_persona_prompt_block(persona)
			+ signal_block
			+ f"Swali la mtumiaji: {question}"
		)
		reply = generate_ai_text(prompt, fallback)
		_store_ai_log(
			request.user,
			question,
			reply,
			persona,
			{
				'quality_label': persona.data_quality_label,
				'completeness': persona.profile_completeness_score,
				'identity_verified': persona.identity_verified,
				'medical_info_verified': persona.medical_info_verified,
				'signal': signal_payload,
			},
		)

		return JsonResponse({'ok': True, 'reply': reply})
