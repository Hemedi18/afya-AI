from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render
from django.views import View
from django.utils import timezone
from collections import Counter

from .services import generate_ai_text, transcribe_audio_file, search_wikipedia, get_disease_info_from_external_apis
from .diagnostic_ai import generate_diagnostic_questions as generate_ai_diagnostic_questions
from .history_ai import build_user_history_context
from .risk_engine import calculate_risk
from .triage_engine import triage_level
from .confidence_engine import calculate_confidence
from .diagnosis_engine import get_possible_conditions
from .differential_ai import generate_differential
from .multistep_ai import multi_step_diagnosis
from .followup_ai import get_last_symptom
from .learning_engine import learn_from_feedback
from users.models import UserAIPersona
from menstrual.models import DailyLog
from .models import AIInteractionLog


# Diagnostic questions database
DIAGNOSTIC_QUESTIONS_DB = {
	'headache': [
		'Jaba la kichwa ni kubwa?',
		'Je nchi inakaanga?',
		'Je umekuwa stressed au exhausted?',
		'Je una maumau ya aim au UV?',
		'Je kichwa kinapigia kwa msimu fulani?',
	],
	'stomachache': [
		'Kumimina ni sana sana?',
		'Je ulikula kitu mbaya?',
		'Je una ugonjwa?',
		'Je dumpling (constipation) au kikomo?',
		'Je maumivu yamekuwa kwa muda gani?',
	],
	'period_pain': [
		'Je jaba ni kama kawaida au kwa nguvu zaidi?',
		'Je una homa?',
		'Je umekuwa na stress?',
		'Je maumivu yanaenea kwenye nyuma?',
		'Je tiba za damu zimebadilike?',
	],
	'cough': [
		'Je kufua kina kitu kinachokuja?',
		'Je una kichwa au maumivu ya koo?',
		'Je una joto la mwili?',
		'Je kufua kumekuwa kwa wiki ngapi?',
		'Je unaoga na kufa kufua?',
	],
	'fever': [
		'Je joto ni kubwa ngapi (celsius)?',
		'Je una maumivu ya mwili?',
		'Je una kufua au kichwa?',
		'Je joto lilipiga lini?',
		'Je umekuwa na teza nyingine?',
	],
}

SYMPTOM_KEYWORDS = {
	'headache': ['kichwa', 'jaba', 'headache', 'aim', 'migreni'],
	'stomachache': ['kumimina', 'meno', 'stomach', 'tummy', 'maumivu ya tumboni'],
	'period_pain': ['maumivu ya menstrua', 'cramping', 'dalili', 'menstrua', 'period'],
	'cough': ['kufua', 'cough', 'coughing', 'koo'],
	'fever': ['joto', 'fever', 'homa', 'temperature'],
}

DISEASE_HINT_KEYWORDS = [
	'ugonjwa', 'maambukizi', 'infection', 'fever', 'homa', 'influenza',
	'migraine', 'uti wa mgongo', 'ulcer', 'pneumonia', 'covid', 'bacteria',
]


def _detect_symptom(question_text):
	"""Detect if question mentions a symptom."""
	question_lower = question_text.lower()
	for symptom, keywords in SYMPTOM_KEYWORDS.items():
		if any(keyword in question_lower for keyword in keywords):
			return symptom
	return None


def _generate_diagnostic_questions(symptom):
	"""Generate diagnostic questions for a symptom."""
	questions = DIAGNOSTIC_QUESTIONS_DB.get(symptom, [])
	return questions[:5]  # Return up to 5 questions


def _is_likely_female(persona):
	gender = (persona.gender or '').strip().lower()
	return gender in {'female', 'f', 'woman', 'mwanamke', 'msichana'}


def _has_recent_period_signal(user):
	recent_logs = DailyLog.objects.filter(
		cycle__user=user,
		date__gte=timezone.now().date() - timezone.timedelta(days=7),
	)
	for log in recent_logs:
		try:
			if int(log.flow_intensity or 0) > 0:
				return True
		except (TypeError, ValueError):
			continue
	return False


def _generate_contextual_diagnostic_questions(user, persona, symptom, question_text=''):
	base = list(_generate_diagnostic_questions(symptom))
	question_lower = (question_text or '').lower()
	is_female = _is_likely_female(persona)
	recent_period = _has_recent_period_signal(user)

	contextual = []
	if symptom == 'stomachache':
		if is_female:
			contextual.append('Kwa sasa upo kwenye siku za hedhi au karibu na hedhi?')
			contextual.append('Maumivu yako yanafanana na maumivu ya hedhi?')
		if recent_period:
			contextual.append('Kwenye logs zako naona period karibuni, maumivu yalianza wakati huo?')
		contextual.append('Ulikula chakula kisicho kawaida ndani ya saa 24 zilizopita?')
		contextual.append('Una dalili ya kuharisha, kufunga choo, au kutapika?')

	if symptom == 'period_pain' and not is_female:
		contextual.insert(0, 'Nikuweke kwenye category ya tumbo badala ya hedhi?')

	if 'tumbo' in question_lower and not symptom:
		contextual.append('Maumivu yako ni sehemu gani ya tumbo (juu/chini/kushoto/kulia)?')

	questions = contextual + base
	unique = []
	seen = set()
	for q in questions:
		if q and q not in seen:
			seen.add(q)
			unique.append(q)
	return unique[:6]


def _generate_pre_answer_questions(user, persona, symptom=None):
	"""Build structured clarification questions from known user data before final answer."""
	questions = []

	if symptom:
		for q in _generate_diagnostic_questions(symptom)[:2]:
			questions.append(q)

	if not persona.permanent_diseases:
		questions.append('Una historia ya ugonjwa wa muda mrefu (mfano pumu, kisukari, pressure)?')
	if not persona.medications:
		questions.append('Kwa sasa unatumia dawa yoyote?')
	if not persona.health_notes:
		questions.append('Kuna allergy au taarifa nyingine muhimu ya afya unayotaka AI izingatie?')

	recent_logs = list(
		DailyLog.objects.filter(cycle__user=user).order_by('-date')[:14]
	)
	if recent_logs:
		top_symptoms = []
		for log in recent_logs:
			for item in (log.physical_symptoms or []):
				if isinstance(item, str) and item.strip():
					top_symptoms.append(item.strip().lower())
		if top_symptoms:
			common = Counter(top_symptoms).most_common(1)[0][0]
			questions.append(f'Dalili hii inafanana na "{common}" uliyoandika karibuni?')

	# Keep unique order and short list for UI clarity
	def _question_key(text):
		return ' '.join((text or '').strip().lower().rstrip('?.!,;:').split())

	unique = []
	seen = set()
	for q in questions:
		key = _question_key(q)
		if key and key not in seen:
			seen.add(key)
			unique.append(q)
	return unique[:4]


def _looks_like_disease_case(question, reply, detected_symptom=None):
	if detected_symptom:
		return True
	combined = f"{question or ''} {reply or ''}".lower()
	return any(word in combined for word in DISEASE_HINT_KEYWORDS)


def _extract_clarification_payload(question_text):
	prefix = 'CLARIFY_DATA:'
	text = (question_text or '').strip()
	if text.upper().startswith(prefix):
		return text[len(prefix):].strip()
	return ''


def _is_ambiguous_reply(reply_text):
	text = (reply_text or '').lower()
	ambiguous_markers = [
		'inaweza', 'huenda', 'kama', 'au', 'sababu nyingi', 'possible',
		'could be', 'might be', 'more than one',
	]
	return any(marker in text for marker in ambiguous_markers)


def _generate_clarification_from_reply(reply_text, fallback_symptom=''):
	text = (reply_text or '').strip()
	if not text:
		return []

	options = []
	parts = [p.strip() for p in text.replace('?', '.').split('.') if p.strip()]
	for part in parts:
		lower = part.lower()
		if ' au ' in lower:
			for bit in part.split('au'):
				clean = bit.strip(' ,;:-')
				if clean and len(clean) > 4:
					options.append(f'Je hali yako inaendana na: {clean}?')

	# Minimal fallback options if parser got nothing
	if not options and fallback_symptom == 'stomachache':
		options = [
			'Maumivu yanafanana na ya hedhi?',
			'Ulikula chakula kisicho kawaida leo?',
			'Una kuharisha au kutapika?',
			'Maumivu yako ni makali upande mmoja wa tumbo?',
		]
	elif not options:
		options = [
			'Dalili hii ilianza ghafla leo?',
			'Dalili inaongezeka ukisogea au ukila?',
			'Una homa, kutapika, au kuishiwa nguvu?',
			'Dalili hii imerudia mara nyingi ndani ya wiki 2?',
		]

	# unique + cap
	unique = []
	seen = set()
	for item in options:
		if item not in seen:
			seen.add(item)
			unique.append(item)
	return unique[:6]


def _normalize_question_items(items):
	"""Merge split fragments so each checkbox item is a complete question."""
	def _question_key(text):
		return ' '.join((text or '').strip().lower().rstrip('?.!,;:').split())

	normalized = []
	buffer = ""

	for raw in (items or []):
		text = (raw or '').strip().lstrip('-•0123456789. ').strip()
		if not text:
			continue

		if buffer:
			buffer = f"{buffer} {text}".strip()
		else:
			buffer = text

		if buffer.endswith('?'):
			normalized.append(buffer)
			buffer = ""

	if buffer:
		# Ensure last fragment still becomes a complete question
		normalized.append(buffer.rstrip(' .,:;!') + '?')

	# De-duplicate with canonical key
	result = []
	seen = set()
	for q in normalized:
		key = _question_key(q)
		if key and key not in seen:
			seen.add(key)
			result.append(q)
	return result


def _split_questions_and_advice(items):
	"""Return (questions_for_checkbox, advisory_text)."""
	questions = []
	advice = []
	seen_questions = set()
	advice_markers = (
		'ushauri', 'tafadhali', 'wasiliana', 'daktari', 'kumbuka', 'epuka', 'unywe',
		'pumzika', 'tembelea', 'hospitali', 'hatari', 'warning'
	)

	def _question_key(text):
		return ' '.join((text or '').strip().lower().rstrip('?.!,;:').split())

	for item in _normalize_question_items(items):
		text = (item or '').strip()
		if not text:
			continue
		lower = text.lower()
		is_question = text.endswith('?') and len(text) > 8 and not any(m in lower for m in advice_markers)
		if is_question:
			q_key = _question_key(text)
			if q_key and q_key not in seen_questions:
				seen_questions.add(q_key)
				questions.append(text)
		else:
			advice.append(text)
	return questions, advice


def _history_context_text(history_context):
	top_symptoms = history_context.get('top_symptoms') or []
	log_symptoms = history_context.get('log_symptoms') or []
	return (
		f"Top symptoms: {top_symptoms}\n"
		f"Recent log symptoms: {log_symptoms}"
	)


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


def _should_use_personal_data(question):
	"""Determine if question is relevant to personal health data."""
	personal_keywords = [
		'yangu', 'nile', 'nilikuwa', 'nimekuwa', 'mimi', 'mialiko', 'majibu',
		'dalili', 'kaput', 'kwa nini', 'nini', 'karibu', 'sasa', 'leo',
	]
	question_lower = question.lower()
	return any(keyword in question_lower for keyword in personal_keywords)


def _generate_smart_suggestions(question, reply, user, persona):
	"""Generate contextual suggestions based on question and reply."""
	suggestions = []
	question_lower = question.lower()
	
	# Topic-based suggestions
	if any(word in question_lower for word in ['mstuko', 'hedachi', 'maumivu', 'mwanzo']):
		suggestions.append({
			'text': 'Jedwali la menstrual cycle',
			'url': 'menstrual:cycle',
			'icon': 'calendar-event'
		})
		suggestions.append({
			'text': 'Kuandika dalili ya asubuhi',
			'url': 'menstrual:log',
			'icon': 'pencil-square'
		})
	
	if any(word in question_lower for word in ['mimba', 'ujauzito', 'hawazimu']):
		suggestions.append({
			'text': 'Vigezo vya ujauzito',
			'url': 'pregnancy:tracker',
			'icon': 'heart'
		})
	
	if any(word in question_lower for word in ['klabu', 'jamii', 'hadithi', 'jamii']):
		suggestions.append({
			'text': 'Jamii lakini salama',
			'url': 'menstrual:community',
			'icon': 'people'
		})
	
	if any(word in question_lower for word in ['daktari', 'tabibika', 'huduma', 'doktor']):
		suggestions.append({
			'text': 'Tafuta daktari au huduma',
			'url': 'doctor:hub',
			'icon': 'hospital'
		})
	
	# Data-driven suggestions - only if profile is reasonably complete
	if persona.profile_completeness_score > 50:
		logs = DailyLog.objects.filter(
			cycle__user=user
		).order_by('-date')[:30]
		
		if logs.exists():
			all_symptoms = []
			for log in logs:
				for item in (log.physical_symptoms or []):
					if isinstance(item, str):
						all_symptoms.append(item.strip())
			
			if all_symptoms:
				top_symptom = Counter(all_symptoms).most_common(1)[0][0]
				suggestions.append({
					'text': f'Karibu na "{top_symptom}" - dalili unayofikiri mara nyingi',
					'url': 'menstrual:reports',
					'icon': 'bar-chart'
				})
	
	# Generic suggestions if few found
	if len(suggestions) < 2:
		suggestions.extend([
			{'text': 'Rejea mafunzo yangu', 'url': 'main:documentation', 'icon': 'book'},
			{'text': 'Huduma za afya', 'url': 'main:services', 'icon': 'briefcase'},
		])
	
	return suggestions[:3]  # Max 3 suggestions


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


def _resolve_chat_input(request):
	question = (request.POST.get('question') or '').strip()
	voice_file = request.FILES.get('voice_file')
	transcript = ''
	input_mode = 'text'

	if voice_file:
		input_mode = 'voice'
		transcript = (transcribe_audio_file(voice_file) or '').strip()
		if transcript and not question:
			question = transcript

	return question, transcript, input_mode


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
				'pre_answer_questions': [],
				'show_disease_deep_dive': False,
				'onboarding_complete': persona.onboarding_complete,
			},
		)

	def post(self, request, *args, **kwargs):
		question, transcript, input_mode = _resolve_chat_input(request)
		persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
		persona.update_quality_metrics(save=True)

		reply = None
		suggestions = []
		diagnostic_questions = []
		clarification_advice = []
		detected_symptom = None
		pre_answer_questions = []
		show_disease_deep_dive = False
		needs_clarification = False
		
		if question:
			fallback = (
				"Asante kwa swali lako. Kwa sasa AI haijapatikana. "
				"Kwa usalama wako, endelea kufuatilia dalili na wasiliana na daktari endapo maumivu ni makali."
			)
			
			clarification_payload = _extract_clarification_payload(question)
			history_context = build_user_history_context(request.user)
			risk_level = calculate_risk(question)
			triage = triage_level(question)
			last_symptom = get_last_symptom(request.user)

			if triage == 'EMERGENCY':
				reply = (
					"🚨 Dalili zako zinaweza kuwa hatari sana. Tafadhali nenda hospitali haraka "
					"au piga huduma ya dharura sasa."
				)
				suggestions = []
				diagnostic_questions = []
				pre_answer_questions = []
				clarification_advice = [
					"Usisubiri nyumbani kama dalili zinaongezeka.",
					"Ukihisi kushindwa kupumua au kupoteza fahamu, tafuta msaada wa haraka.",
				]
				needs_clarification = False
				show_disease_deep_dive = False
				confidence_score = calculate_confidence(persona, history_context, None)
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
						'signal': {},
						'used_personal_data': _should_use_personal_data(question),
						'symptom_detected': None,
						'triage': triage,
						'risk_level': risk_level,
						'confidence_score': confidence_score,
						'history_context': history_context,
					},
				)
				return render(
					request,
					self.template_name,
					{
						'reply': reply,
						'question': question,
						'suggestions': suggestions,
						'diagnostic_questions': diagnostic_questions,
						'symptom': detected_symptom,
						'pre_answer_questions': pre_answer_questions,
						'show_disease_deep_dive': False,
						'needs_clarification': False,
						'clarification_advice': clarification_advice,
						'onboarding_complete': persona.onboarding_complete,
					},
				)

			diag_signal_block = ""
			if persona.ai_data_consent:
				diag_signal_block, _ = _build_recent_health_signal_block(request.user)
			# Detect if user is describing symptoms
			detected_symptom = None if clarification_payload else _detect_symptom(question)
			if detected_symptom:
				raw_questions = generate_ai_diagnostic_questions(
					question=question,
					persona=persona,
					signal_block=diag_signal_block,
					symptom_hint=detected_symptom,
				)
				diagnostic_questions, clarification_advice = _split_questions_and_advice(raw_questions)
			pre_answer_questions = _generate_pre_answer_questions(request.user, persona, detected_symptom)
			confidence_score = calculate_confidence(persona, history_context, detected_symptom)
			possible_conditions = get_possible_conditions(detected_symptom) if detected_symptom else []
			
			# Only include personal data if question is relevant to personal health
			signal_block, signal_payload = "", {}
			use_personal_data = _should_use_personal_data(question) or bool(detected_symptom) or bool(clarification_payload)
			if use_personal_data:
				signal_block, signal_payload = _build_recent_health_signal_block(request.user)
			
			system_instructions = (
				"You are a compassionate women's health AI assistant. "
				"Respond in simple Swahili. Be empathetic, practical, medically safe, and avoid panic. "
				"IMPORTANT: Only reference personal data if the question clearly asks about the user's health. "
				"If the user asks general questions (like 'what causes...'), give general safe answers without personal data. "
				"Always end with a safety note if discussing concerning symptoms."
			)
			
			if diagnostic_questions and not clarification_payload:
				needs_clarification = True
				clarification_advice = []
				reply = (
					"Nimeona kuna sababu zaidi ya moja. Kabla ya jibu la mwisho, "
					"chagua options kwenye checkbox ili nifanye uchambuzi sahihi kulingana na data yako. "
					f"(Confidence: {confidence_score}%)"
				)
				suggestions = []
				show_disease_deep_dive = False
			else:
				history_text = _history_context_text(history_context)
				differential_text = generate_differential(question, history_text)
				multistep_text = multi_step_diagnosis(question, history_text, risk_level)
				prompt = (
					system_instructions + "\n\n"
					+ _build_quality_rules_block(persona)
					+ _build_persona_prompt_block(persona)
					+ signal_block
					+ f"Clinical triage: {triage}\n"
					+ f"Risk level: {risk_level}\n"
					+ f"Confidence score baseline: {confidence_score}%\n"
					+ f"Possible conditions from dataset: {possible_conditions}\n"
					+ f"History context:\n{history_text}\n"
					+ (f"Last symptom from previous chats: {last_symptom}\n" if last_symptom else "")
					+ f"Differential snapshot:\n{differential_text}\n"
					+ f"Multi-step snapshot:\n{multistep_text}\n"
					+ "Think deeply first using available profile/log context. Do not reveal chain-of-thought. "
					+ "Before any final conclusion, identify missing facts and keep response medically safe.\n\n"
					+ (f"User clarification answers: {clarification_payload}\n" if clarification_payload else "")
					+ f"User question: {question}"
				)
				reply = generate_ai_text(prompt, fallback)
				if _is_ambiguous_reply(reply):
					needs_clarification = True
					raw_questions = _generate_clarification_from_reply(reply, detected_symptom or '')
					diagnostic_questions, clarification_advice = _split_questions_and_advice(raw_questions)
					clarification_advice = []
					reply = (
						"Bado kuna options zaidi ya moja. Tafadhali chagua checkbox ili nipunguze "
						"hadi nipate chanzo sahihi zaidi."
					)
					suggestions = []
					show_disease_deep_dive = False
				else:
					suggestions = _generate_smart_suggestions(question, reply, request.user, persona)
					show_disease_deep_dive = False
			
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
					'used_personal_data': use_personal_data,
					'symptom_detected': detected_symptom,
					'triage': triage,
					'risk_level': risk_level,
					'confidence_score': confidence_score,
					'possible_conditions': possible_conditions,
					'history_context': history_context,
					'last_symptom': last_symptom,
				},
			)

		return render(
			request,
			self.template_name,
			{
				'reply': reply,
				'question': transcript or question,
				'suggestions': suggestions,
				'diagnostic_questions': diagnostic_questions,
				'symptom': detected_symptom,
				'pre_answer_questions': pre_answer_questions if question else [],
				'show_disease_deep_dive': show_disease_deep_dive if question else False,
				'needs_clarification': needs_clarification if question else False,
				'clarification_advice': clarification_advice if question else [],
				'onboarding_complete': persona.onboarding_complete,
				'input_mode': input_mode,
			},
		)


class AIQuickChatView(LoginRequiredMixin, View):
	def post(self, request, *args, **kwargs):
		question, transcript, input_mode = _resolve_chat_input(request)
		if not question:
			message = 'Tafadhali andika swali.'
			if input_mode == 'voice':
				message = 'Sauti haijasomeka vizuri. Jaribu kurekodi tena kwa sauti wazi.'
			return JsonResponse({'ok': False, 'error': message}, status=400)

		persona, _ = UserAIPersona.objects.get_or_create(user=request.user)
		persona.update_quality_metrics(save=True)
		fallback = (
			"Samahani, kwa sasa AI haijapatikana. "
			"Kwa usalama wako, fuatilia dalili zako na wasiliana na daktari kama maumivu ni makali."
		)
		
		clarification_payload = _extract_clarification_payload(question)
		history_context = build_user_history_context(request.user)
		risk_level = calculate_risk(question)
		triage = triage_level(question)
		last_symptom = get_last_symptom(request.user)

		if triage == 'EMERGENCY':
			reply = (
				"🚨 Dalili zako zinaweza kuwa hatari sana. Tafadhali nenda hospitali haraka "
				"au piga huduma ya dharura sasa."
			)
			suggestions = []
			diagnostic_questions = []
			clarification_advice = [
				"Usisubiri nyumbani kama dalili zinaongezeka.",
				"Ukihisi kushindwa kupumua au kupoteza fahamu, tafuta msaada wa haraka.",
			]
			pre_answer_questions = []
			needs_clarification = False
			show_disease_deep_dive = False
			confidence_score = calculate_confidence(persona, history_context, None)
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
					'signal': {},
					'used_personal_data': _should_use_personal_data(question),
					'symptom_detected': None,
					'triage': triage,
					'risk_level': risk_level,
					'confidence_score': confidence_score,
					'history_context': history_context,
				},
			)
			return JsonResponse({
				'ok': True,
				'reply': reply,
				'transcript': transcript,
				'input_mode': input_mode,
				'suggestions': suggestions,
				'diagnostic_questions': diagnostic_questions,
				'symptom': None,
				'pre_answer_questions': pre_answer_questions,
				'show_disease_deep_dive': False,
				'needs_clarification': False,
				'clarification_advice': clarification_advice,
				'triage': triage,
				'risk_level': risk_level,
				'confidence_score': confidence_score,
			})

		diag_signal_block = ""
		if persona.ai_data_consent:
			diag_signal_block, _ = _build_recent_health_signal_block(request.user)
		# Detect if user is describing symptoms
		detected_symptom = None if clarification_payload else _detect_symptom(question)
		diagnostic_questions = []
		clarification_advice = []
		if detected_symptom:
			raw_questions = generate_ai_diagnostic_questions(
				question=question,
				persona=persona,
				signal_block=diag_signal_block,
				symptom_hint=detected_symptom,
			)
			diagnostic_questions, clarification_advice = _split_questions_and_advice(raw_questions)
		pre_answer_questions = _generate_pre_answer_questions(request.user, persona, detected_symptom)
		confidence_score = calculate_confidence(persona, history_context, detected_symptom)
		possible_conditions = get_possible_conditions(detected_symptom) if detected_symptom else []
		needs_clarification = bool(diagnostic_questions) and not bool(clarification_payload)
		
		# Only include personal data if question is relevant to personal health
		signal_block, signal_payload = "", {}
		use_personal_data = _should_use_personal_data(question) or bool(detected_symptom) or bool(clarification_payload)
		if use_personal_data:
			signal_block, signal_payload = _build_recent_health_signal_block(request.user)
		
		system_instructions = (
			"You are a compassionate women's health AI assistant. "
			"Respond in simple Swahili. Be empathetic, practical, medically safe, and avoid panic. "
			"IMPORTANT: Only reference personal data if the question clearly asks about the user's health. "
			"If the user asks general questions (like 'what causes...'), give general safe answers without personal data. "
			"Always end with a safety note if discussing concerning symptoms."
		)
		
		if needs_clarification:
			clarification_advice = []
			reply = (
				"Nimeona kuna sababu zaidi ya moja. Kabla ya jibu la mwisho, "
				"chagua options kwenye checkbox ili nifanye uchambuzi sahihi kulingana na data yako. "
				f"(Confidence: {confidence_score}%)"
			)
			suggestions = []
			show_disease_deep_dive = False
		else:
			history_text = _history_context_text(history_context)
			differential_text = generate_differential(question, history_text)
			multistep_text = multi_step_diagnosis(question, history_text, risk_level)
			prompt = (
				system_instructions + "\n\n"
				+ _build_quality_rules_block(persona)
				+ _build_persona_prompt_block(persona)
				+ signal_block
				+ f"Clinical triage: {triage}\n"
				+ f"Risk level: {risk_level}\n"
				+ f"Confidence score baseline: {confidence_score}%\n"
				+ f"Possible conditions from dataset: {possible_conditions}\n"
				+ f"History context:\n{history_text}\n"
				+ (f"Last symptom from previous chats: {last_symptom}\n" if last_symptom else "")
				+ f"Differential snapshot:\n{differential_text}\n"
				+ f"Multi-step snapshot:\n{multistep_text}\n"
				+ "Think deeply first using available profile/log context. Do not reveal chain-of-thought. "
				+ "Before any final conclusion, identify missing facts and keep response medically safe.\n\n"
				+ (f"User clarification answers: {clarification_payload}\n" if clarification_payload else "")
				+ f"User question: {question}"
			)
			reply = generate_ai_text(prompt, fallback)
			if _is_ambiguous_reply(reply):
				needs_clarification = True
				raw_questions = _generate_clarification_from_reply(reply, detected_symptom or '')
				diagnostic_questions, clarification_advice = _split_questions_and_advice(raw_questions)
				clarification_advice = []
				reply = (
					"Bado kuna options zaidi ya moja. Tafadhali chagua checkbox ili nipunguze "
					"hadi nipate chanzo sahihi zaidi."
				)
				suggestions = []
				show_disease_deep_dive = False
			else:
				suggestions = _generate_smart_suggestions(question, reply, request.user, persona)
				show_disease_deep_dive = False
		
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
				'used_personal_data': use_personal_data,
				'symptom_detected': detected_symptom,
				'triage': triage,
				'risk_level': risk_level,
				'confidence_score': confidence_score,
				'possible_conditions': possible_conditions,
				'history_context': history_context,
				'last_symptom': last_symptom,
			},
		)

		return JsonResponse({
			'ok': True,
			'reply': reply,
			'transcript': transcript,
			'input_mode': input_mode,
			'suggestions': suggestions,
			'diagnostic_questions': diagnostic_questions,
			'symptom': detected_symptom,
			'pre_answer_questions': pre_answer_questions,
			'show_disease_deep_dive': show_disease_deep_dive,
			'needs_clarification': needs_clarification,
			'clarification_advice': clarification_advice,
			'triage': triage,
			'risk_level': risk_level,
			'confidence_score': confidence_score,
		})


class AIFeedbackView(LoginRequiredMixin, View):
	def post(self, request, *args, **kwargs):
		rating = (request.POST.get('rating') or '').strip().lower()
		last_question = (request.POST.get('last_question') or '').strip()
		last_reply = (request.POST.get('last_reply') or '').strip()

		if rating not in {'up', 'down'}:
			return JsonResponse({'ok': False, 'error': 'Rating is required.'}, status=400)

		feedback_payload = {
			'rating': rating,
			'last_question': last_question,
			'last_reply': last_reply,
		}
		learn_from_feedback(request.user, feedback_payload)

		return JsonResponse({'ok': True, 'message': 'Asante kwa feedback yako.'})
