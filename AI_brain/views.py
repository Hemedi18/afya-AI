from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from .services import generate_ai_text
from users.models import UserAIPersona


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


class AIChatView(LoginRequiredMixin, View):
	template_name = 'AI_brain/ai_chat.html'

	def get(self, request, *args, **kwargs):
		persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
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

		reply = None
		if question:
			fallback = (
				"Asante kwa swali lako. Kwa sasa AI haijapatikana. "
				"Kwa usalama wako, endelea kufuatilia dalili na wasiliana na daktari endapo maumivu ni makali."
			)
			prompt = _build_persona_prompt_block(persona) + f"Swali la mtumiaji: {question}"
			reply = generate_ai_text(prompt, fallback)

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
		fallback = (
			"Samahani, kwa sasa AI haijapatikana. "
			"Kwa usalama wako, fuatilia dalili zako na wasiliana na daktari kama maumivu ni makali."
		)
		prompt = _build_persona_prompt_block(persona) + f"Swali la mtumiaji: {question}"
		reply = generate_ai_text(prompt, fallback)

		return JsonResponse({'ok': True, 'reply': reply})
