from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.utils import timezone

import json
from collections import Counter

from menstrual.models import CommunityPost
from users.utils import get_user_gender

from .forms import CoupleConnectForm, PubertyCheckForm, PubertyFindingForm, PubertyHabitGoalForm, ReproductiveMetricEntryForm
from .models import AIScoreSnapshot, CoupleConnection, PubertyCheckRecord, PubertyFinding, PubertyHabitGoal, PubertyPreventionPlanDay, ReproductiveMetricEntry


User = get_user_model()


REPRO_HEALTH_ISSUES = [
	{
		'name': 'STI Infections',
		'problem': 'Discharge isiyo ya kawaida, vidonda, kuwasha, maumivu wakati wa kukojoa.',
		'solution': 'Pima mapema, epuka kujitibu holela, tumia kinga, na pata ushauri wa daktari.',
		'urgent': 'Vidonda, homa kali, au maumivu makali ya nyonga.',
	},
	{
		'name': 'Irregular periods',
		'problem': 'Mzunguko usiotabirika, kuchelewa sana au kuja mara kwa mara.',
		'solution': 'Fuatilia cycle, punguza stress, boresha lishe na usingizi, fanya checkup kama inaendelea.',
		'urgent': 'Kutopata hedhi > siku 90 au damu nyingi sana mfululizo.',
	},
	{
		'name': 'Severe menstrual pain',
		'problem': 'Maumivu makali ya hedhi yanayoathiri shule/kazi.',
		'solution': 'Warm compress, hydration, exercise nyepesi, mazungumzo na mtaalamu wa afya.',
		'urgent': 'Maumivu yasiyovumilika, kuzimia, au kutokwa damu nyingi sana.',
	},
	{
		'name': 'Puberty anxiety & body changes stress',
		'problem': 'Aibu, kujitenga, hofu ya mabadiliko ya mwili.',
		'solution': 'Pata elimu sahihi, support group, na journaling ya hisia.',
		'urgent': 'Mawazo ya kujidhuru au msongo mkali unaoathiri maisha.',
	},
	{
		'name': 'Male reproductive concerns',
		'problem': 'Maumivu ya korodani, uvimbe, erection issues.',
		'solution': 'Usichelewe clinic, epuka dawa za mitaani, boresha mtindo wa maisha.',
		'urgent': 'Maumivu ya ghafla ya korodani, uvimbe mkubwa, damu kwenye shahawa.',
	},
]


HIGH_RISK_SYMPTOMS = {
	'genital_sores',
	'testicular_pain',
	'breast_lump',
	'heavy_bleeding',
}

RED_FLAG_NOTES = {
	'faint',
	'kuzimia',
	'blood clots',
	'damu nyingi',
	'suicidal',
	'kujidhuru',
	'severe pain',
}


FEATURE_SECTIONS = {
	'mens_hub': {
		'title': "Men's Health & Performance Hub",
		'items': [
			'PE Tracker, ED Log, Libido Monitor, Morning Testosterone Indicator',
			'Recovery Time Tracker, Stamina Training Programs, Pelvic Floor Analyzer',
			'Sex Frequency Tracker, Confidence Score AI, Fertility & Sperm Guide',
			'Heat Exposure Tracker, Sleep vs Testosterone, Supplements Reminder',
		],
	},
	'womens_hub': {
		'title': "Women's Health & Wellness Hub",
		'items': [
			'Advanced Period Tracker, PMS/PMDD Logger, PCOS/Endometriosis Monitor',
			'Hormone Balance AI Score, Cycle Prediction AI, Ovulation Symptoms Logger',
			'Dyspareunia Locator, Vaginismus Support, Vaginal Health Checker',
			'Lubrication Tracker, Pelvic Floor Training, Fertility Score AI',
		],
	},
	'ai_core': {
		'title': 'AI Core System',
		'items': [
			'Anonymous AI Therapist, Symptom Triage, AI Report Generator',
			'AI Daily Health Coach, AI Risk Prediction Engine, Personalized Advice',
			'AI Health Score, Fertility Score, Sexual Performance Score',
			'AI Hormone Score + Stress vs Libido Analysis',
		],
	},
	'security': {
		'title': 'Security & Privacy',
		'items': [
			'Disguise Mode, PIN Lock concept, Hidden Notifications',
			'Auto-destruct chat strategy, Offline mode friendly design',
			'Data privacy-first approach and anonymous sharing support',
		],
	},
}


def _evaluate_risk(symptoms: list[str], severity: int) -> tuple[str, bool]:
	symptoms_set = set(symptoms or [])
	if severity >= 4 or symptoms_set.intersection(HIGH_RISK_SYMPTOMS):
		return PubertyCheckRecord.RISK_HIGH, True
	if severity >= 3 or len(symptoms_set) >= 3:
		return PubertyCheckRecord.RISK_MEDIUM, False
	return PubertyCheckRecord.RISK_LOW, False


def _build_guidance(symptoms: list[str], risk_level: str, notes: str = '') -> str:
	symptom_text = ', '.join(symptoms) if symptoms else 'No major symptoms selected.'
	base = [
		f'Symptoms zilizochaguliwa: {symptom_text}.',
		'Hatua za msingi: kunywa maji ya kutosha, usafi wa sehemu za siri, na usingizi wa saa 7-8.',
	]

	if risk_level == PubertyCheckRecord.RISK_HIGH:
		base.append('Risk level ni HIGH: tafadhali fika kituo cha afya haraka kwa uchunguzi wa kitaalamu.')
	elif risk_level == PubertyCheckRecord.RISK_MEDIUM:
		base.append('Risk level ni MEDIUM: endelea kufuatilia dalili ndani ya siku 2-7, na fanya clinic visit zikizidi.')
	else:
		base.append('Risk level ni LOW: endelea kujitunza, fuatilia mabadiliko, na weka healthy routine.')

	if notes:
		base.append('Ujumbe wako umezingatiwa. Kama dalili zinabadilika ghafla, tafuta msaada wa daktari.')

	return ' '.join(base)


def _detect_advanced_red_flags(symptoms: list[str], notes: str) -> list[str]:
	flags = []
	symptoms_set = set(symptoms or [])
	notes_text = (notes or '').lower()

	if 'heavy_bleeding' in symptoms_set:
		flags.append('Heavy bleeding detected')
	if 'genital_sores' in symptoms_set:
		flags.append('Possible STI red flag (genital sores)')
	if 'testicular_pain' in symptoms_set:
		flags.append('Possible testicular emergency')
	if 'breast_lump' in symptoms_set:
		flags.append('Breast lump requires clinical evaluation')

	for token in RED_FLAG_NOTES:
		if token in notes_text:
			flags.append(f'Red flag phrase in notes: {token}')

	return flags


def _build_prevention_plan(symptoms: list[str], gender: str, risk_level: str) -> list[dict]:
	base_plan = [
		{'title': 'Hydration & Hygiene', 'action': 'Kunywa glasi 6-8 za maji na fanya usafi wa sehemu za siri kwa upole.'},
		{'title': 'Sleep Reset', 'action': 'Lala masaa 7-8 na punguza matumizi ya simu kabla ya kulala.'},
		{'title': 'Nutrition Day', 'action': 'Ongeza mboga, matunda, na protini nyepesi ili kuimarisha homoni na kinga.'},
		{'title': 'Stress Control', 'action': 'Fanya mazoezi mepesi dakika 20 na deep breathing mara 2 kwa siku.'},
		{'title': 'Symptom Tracking', 'action': 'Andika dalili, muda, na ukali wake kwenye app ili kuona trend.'},
		{'title': 'Safe Habits', 'action': 'Epuka ngono isiyo salama, tumia kinga, na usitumie dawa bila ushauri.'},
		{'title': 'Review & Action', 'action': 'Pitia dalili zako. Zikiongezeka au kuwa za hatari, fika kliniki haraka.'},
	]

	if gender == 'female' and 'irregular_periods' in (symptoms or []):
		base_plan[4]['action'] = 'Track mzunguko wa hedhi kila siku na andika trigger kama stress/lishe.'
	if gender == 'male' and 'testicular_pain' in (symptoms or []):
		base_plan[6]['action'] = 'Maumivu ya korodani yakiendelea au kuwa makali, nenda emergency leo.'
	if risk_level == PubertyCheckRecord.RISK_HIGH:
		base_plan[6]['action'] = 'Risk ni HIGH: panga clinic visit ndani ya saa 24.'

	return base_plan


def _clamp_score(value: float) -> int:
	return max(0, min(100, int(round(value))))


def _build_ai_scores(user, latest_check, goals, metrics) -> dict:
	overall = 72.0
	fertility = 70.0
	performance = 68.0
	hormone = 69.0
	stress_libido = 66.0

	if latest_check:
		if latest_check.risk_level == PubertyCheckRecord.RISK_HIGH:
			overall -= 25
			fertility -= 18
			performance -= 16
			hormone -= 12
			stress_libido -= 20
		elif latest_check.risk_level == PubertyCheckRecord.RISK_MEDIUM:
			overall -= 12
			fertility -= 8
			performance -= 8
			hormone -= 6
			stress_libido -= 10

	goal_bonus = min(len(goals) * 2, 10)
	overall += goal_bonus
	stress_libido += goal_bonus

	for m in metrics[:20]:
		key = (m.metric_key or '').lower()
		val = m.metric_value
		if key in {'sleep_hours', 'sleep_quality'} and val >= 7:
			hormone += 4
			performance += 2
		if key in {'exercise_minutes', 'workout_score'} and val >= 30:
			performance += 4
			stress_libido += 3
		if key in {'stress_level', 'anxiety'} and val >= 7:
			stress_libido -= 8
		if key in {'heat_exposure', 'toxin_exposure'} and val >= 6:
			fertility -= 6

	scores = {
		'overall_score': _clamp_score(overall),
		'fertility_score': _clamp_score(fertility),
		'sexual_performance_score': _clamp_score(performance),
		'hormone_balance_score': _clamp_score(hormone),
		'stress_libido_score': _clamp_score(stress_libido),
	}
	return scores


@login_required
def dashboard(request):
	checks = PubertyCheckRecord.objects.filter(user=request.user)[:5]
	goals = PubertyHabitGoal.objects.filter(user=request.user)[:5]
	findings = PubertyFinding.objects.filter(user=request.user)[:5]
	metrics = ReproductiveMetricEntry.objects.filter(user=request.user)[:8]
	latest_check = PubertyCheckRecord.objects.filter(user=request.user).first()
	latest_plan = latest_check.prevention_plan_days.all() if latest_check else []
	ai_scores = _build_ai_scores(request.user, latest_check, goals, ReproductiveMetricEntry.objects.filter(user=request.user))
	today = timezone.now().date()
	if not AIScoreSnapshot.objects.filter(user=request.user, created_at__date=today).exists():
		AIScoreSnapshot.objects.create(
			user=request.user,
			summary='Auto-generated from checks, habits, and metric logs.',
			**ai_scores,
		)
	couple_connection = CoupleConnection.objects.filter(requester=request.user).first() or CoupleConnection.objects.filter(partner=request.user, status=CoupleConnection.STATUS_ACCEPTED).first()

	last_30 = timezone.now() - timezone.timedelta(days=30)
	check_30 = PubertyCheckRecord.objects.filter(user=request.user, created_at__gte=last_30)
	risk_counts = {'low': 0, 'medium': 0, 'high': 0}
	symptom_counter = Counter()
	for item in check_30:
		risk_counts[item.risk_level] = risk_counts.get(item.risk_level, 0) + 1
		symptom_counter.update(item.symptoms or [])

	top_symptoms = symptom_counter.most_common(6)

	context = {
		'feature_sections': FEATURE_SECTIONS,
		'issues': REPRO_HEALTH_ISSUES,
		'checks': checks,
		'goals': goals,
		'findings': findings,
		'metrics': metrics,
		'ai_scores': ai_scores,
		'couple_connection': couple_connection,
		'latest_plan': latest_plan,
		'chart_risk_labels': json.dumps(['Low', 'Medium', 'High']),
		'chart_risk_data': json.dumps([risk_counts.get('low', 0), risk_counts.get('medium', 0), risk_counts.get('high', 0)]),
		'chart_symptom_labels': json.dumps([name for name, _ in top_symptoms]),
		'chart_symptom_data': json.dumps([count for _, count in top_symptoms]),
		'check_form': PubertyCheckForm(),
		'goal_form': PubertyHabitGoalForm(),
		'finding_form': PubertyFindingForm(),
		'metric_form': ReproductiveMetricEntryForm(),
		'couple_form': CoupleConnectForm(),
	}
	return render(request, 'reproduction/dashboard.html', context)


@login_required
@require_POST
def create_check(request):
	form = PubertyCheckForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Tafadhali jaza form ya self-check vizuri.')
		return redirect('reproduction:dashboard')

	check = form.save(commit=False)
	check.user = request.user
	symptoms = form.cleaned_data.get('symptoms') or []
	check.symptoms = symptoms
	check.risk_level, check.needs_doctor = _evaluate_risk(symptoms, check.severity)
	red_flags = _detect_advanced_red_flags(symptoms, check.notes)
	if red_flags:
		check.needs_doctor = True
		check.risk_level = PubertyCheckRecord.RISK_HIGH
	check.red_flags = red_flags
	check.ai_guidance = _build_guidance(symptoms, check.risk_level, check.notes)
	check.save()

	gender = (check.gender or get_user_gender(request.user) or 'other').lower()
	for i, item in enumerate(_build_prevention_plan(symptoms, gender, check.risk_level), start=1):
		PubertyPreventionPlanDay.objects.create(
			check_record=check,
			day_number=i,
			title=item['title'],
			action=item['action'],
		)

	if check.needs_doctor:
		messages.warning(request, 'Dalili zako zinaonyesha red flags. Tafadhali wasiliana na daktari mapema.')
	else:
		messages.success(request, 'Self-check imehifadhiwa + prevention plan ya siku 7 imetengenezwa.')
	return redirect('reproduction:dashboard')


@login_required
@require_POST
def create_goal(request):
	form = PubertyHabitGoalForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Goal haijahifadhiwa. Angalia taarifa ulizoingiza.')
		return redirect('reproduction:dashboard')

	goal = form.save(commit=False)
	goal.user = request.user
	goal.save()
	messages.success(request, 'Healthy habit goal imeongezwa.')
	return redirect('reproduction:dashboard')


@login_required
@require_POST
def toggle_goal_today(request, goal_id: int):
	goal = get_object_or_404(PubertyHabitGoal, id=goal_id, user=request.user)
	goal.completed_today = not goal.completed_today
	if goal.completed_today:
		goal.streak_days += 1
	elif goal.streak_days > 0:
		goal.streak_days -= 1
	goal.save(update_fields=['completed_today', 'streak_days', 'updated_at'])
	return redirect('reproduction:dashboard')


@login_required
@require_POST
def create_finding(request):
	form = PubertyFindingForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Finding haijahifadhiwa. Tafadhali hakiki form.')
		return redirect('reproduction:dashboard')

	finding = form.save(commit=False)
	finding.user = request.user
	finding.save()

	if finding.share_to_community:
		gender = get_user_gender(request.user) or 'female'
		content = f"[Puberty Finding] {finding.title}\n\n{finding.finding}\n\nTags: {finding.tags}"
		post = CommunityPost.objects.create(
			user=request.user,
			content=content,
			is_anonymous=finding.is_anonymous,
			audience_gender=gender if gender in {'female', 'male'} else 'female',
		)
		finding.community_post = post
		finding.save(update_fields=['community_post'])
		messages.success(request, 'Finding imehifadhiwa na kushare kwenye Jamii app.')
	else:
		messages.success(request, 'Finding imehifadhiwa private.')

	return redirect('reproduction:dashboard')


@login_required
@require_POST
def create_metric(request):
	form = ReproductiveMetricEntryForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Metric haijahifadhiwa. Tafadhali hakiki taarifa.')
		return redirect('reproduction:dashboard')

	entry = form.save(commit=False)
	entry.user = request.user
	entry.save()
	messages.success(request, 'Metric log imehifadhiwa kwa AI learning.')
	return redirect('reproduction:dashboard')


@login_required
@require_POST
def connect_couple(request):
	form = CoupleConnectForm(request.POST)
	if not form.is_valid():
		messages.error(request, 'Ingiza username sahihi ya partner.')
		return redirect('reproduction:dashboard')

	username = form.cleaned_data['partner_username'].strip()
	partner = User.objects.filter(username__iexact=username).exclude(id=request.user.id).first()
	if not partner:
		messages.error(request, 'Partner hakupatikana.')
		return redirect('reproduction:dashboard')

	obj, created = CoupleConnection.objects.get_or_create(
		requester=request.user,
		partner=partner,
		defaults={'status': CoupleConnection.STATUS_PENDING},
	)
	if created:
		messages.success(request, 'Couples request imetumwa.')
	else:
		messages.info(request, f'Couples request tayari ipo ({obj.status}).')
	return redirect('reproduction:dashboard')
