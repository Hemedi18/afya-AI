import json
import ipaddress
import statistics

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from .forms import DoctorRegistrationForm
from .models import (
	DoctorFollow, DoctorRating, DoctorReport, DoctorVerificationRequest,
	PatientLog, PatientLogEntry, PatientLogField,
)
from chats.models import PrivateConversation
from menstrual.models import CommunityPost, DoctorProfile
from users.permissions import AdminRequiredMixin, is_admin, is_doctor
from users.utils import get_user_gender
from users.models import UserAIPersona


def _get_client_ip(request):
	forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
	if forwarded:
		return forwarded.split(',')[0].strip()
	return (request.META.get('REMOTE_ADDR') or '').strip()


def _mask_ip(ip_raw):
	if not ip_raw:
		return 'unknown'
	try:
		ip_obj = ipaddress.ip_address(ip_raw)
		if ip_obj.version == 4:
			parts = ip_raw.split('.')
			return f'{parts[0]}.{parts[1]}.x.x'
		# IPv6: keep only first 3 hextets for approximate info
		hextets = ip_raw.split(':')
		return ':'.join(hextets[:3]) + '::'
	except ValueError:
		return 'unknown'


def _detect_device_type(request):
	ua = (request.META.get('HTTP_USER_AGENT') or '').lower()
	if any(k in ua for k in ('mobile', 'android', 'iphone', 'ipod')):
		return 'mobile'
	if 'ipad' in ua or 'tablet' in ua:
		return 'tablet'
	if ua:
		return 'desktop'
	return 'unknown'


def _detect_session_source(request):
	ua = (request.META.get('HTTP_USER_AGENT') or '').lower()
	if any(k in ua for k in ('wv', 'webview', 'okhttp')):
		return 'app-webview'
	if request.headers.get('x-requested-with') == 'XMLHttpRequest':
		return 'ajax-web'
	ref = request.META.get('HTTP_REFERER')
	if ref:
		return 'web-referrer'
	return 'web-direct'


class DoctorHubView(LoginRequiredMixin, View):
	template_name = 'doctor/hub.html'

	def get(self, request, *args, **kwargs):
		user_gender = get_user_gender(request.user)
		selected_gender = request.GET.get('gender')
		q = (request.GET.get('q') or '').strip()
		doctors = DoctorProfile.objects.select_related('user').annotate(
			rank_avg=Avg('ratings__score'),
			rank_count=Count('ratings', distinct=True),
			report_count=Count('reports', distinct=True),
			followers_count=Count('followers', distinct=True),
		).order_by('-verified', '-rank_avg', 'user__username')
		if selected_gender in {'female', 'male'}:
			doctors = doctors.filter(gender=selected_gender)
		elif user_gender in {'female', 'male'}:
			doctors = doctors.filter(gender=user_gender)
		if q:
			doctors = doctors.filter(
				Q(user__username__icontains=q)
				| Q(user__first_name__icontains=q)
				| Q(user__last_name__icontains=q)
				| Q(specialization__icontains=q)
				| Q(hospital_name__icontains=q)
			)
		my_profile = DoctorProfile.objects.filter(user=request.user).first()
		pending_requests = DoctorVerificationRequest.objects.filter(status=DoctorVerificationRequest.STATUS_PENDING).count()
		current_filter = selected_gender if selected_gender in {'female', 'male'} else user_gender
		my_followed_ids = set(DoctorFollow.objects.filter(follower=request.user).values_list('doctor_profile_id', flat=True))
		return render(
			request,
			self.template_name,
			{
				'doctors': doctors,
				'verified_count': doctors.filter(verified=True).count(),
				'my_followed_ids': my_followed_ids,
				'my_doctor_profile': my_profile,
				'can_manage_doctors': is_admin(request.user),
				'is_doctor_account': is_doctor(request.user),
				'pending_requests': pending_requests,
				'user_gender': user_gender,
				'selected_doctor_gender': current_filter,
				'search_query': q,
			},
		)


class DoctorDetailView(LoginRequiredMixin, View):
	template_name = 'doctor/detail.html'

	def get(self, request, doctor_id, *args, **kwargs):
		doctor = get_object_or_404(
			DoctorProfile.objects.select_related('user').annotate(
				rank_avg=Avg('ratings__score'),
				rank_count=Count('ratings', distinct=True),
				report_count=Count('reports', distinct=True),
				followers_count=Count('followers', distinct=True),
			),
			pk=doctor_id,
		)
		doctor_posts = CommunityPost.objects.filter(user=doctor.user).select_related('group').prefetch_related('groups', 'likes', 'media_items').order_by('-created_at')[:50]
		is_following = DoctorFollow.objects.filter(follower=request.user, doctor_profile=doctor).exists()
		today = timezone.localdate()
		chatted_today = PrivateConversation.objects.filter(
			doctor=doctor.user,
			patient=request.user,
			updated_at__date=today,
		).exists()
		rated_today = DoctorRating.objects.filter(rater=request.user, doctor_profile=doctor, created_at__date=today).exists()
		can_rate_today = chatted_today and not rated_today and request.user != doctor.user
		my_rating_today = DoctorRating.objects.filter(rater=request.user, doctor_profile=doctor, created_at__date=today).first()
		return render(
			request,
			self.template_name,
			{
				'doctor': doctor,
				'doctor_posts': doctor_posts,
				'is_following': is_following,
				'can_rate_today': can_rate_today,
				'my_rating_today': my_rating_today,
				'chatted_today': chatted_today,
			},
		)


class DoctorFollowToggleView(LoginRequiredMixin, View):
	def post(self, request, doctor_id, *args, **kwargs):
		doctor = get_object_or_404(DoctorProfile, pk=doctor_id)
		if doctor.user == request.user:
			messages.info(request, 'Huwezi kujifollow mwenyewe.')
			return redirect('doctor:detail', doctor_id=doctor.id)
		obj = DoctorFollow.objects.filter(follower=request.user, doctor_profile=doctor).first()
		if obj:
			obj.delete()
			messages.success(request, 'Umeondoa follow kwa doctor huyu.')
		else:
			DoctorFollow.objects.create(follower=request.user, doctor_profile=doctor)
			messages.success(request, 'Umeanza kumfollow doctor huyu.')
		return redirect('doctor:detail', doctor_id=doctor.id)


class DoctorRateView(LoginRequiredMixin, View):
	def post(self, request, doctor_id, *args, **kwargs):
		doctor = get_object_or_404(DoctorProfile, pk=doctor_id)
		if doctor.user == request.user:
			messages.info(request, 'Huwezi kujirank mwenyewe.')
			return redirect('doctor:detail', doctor_id=doctor.id)

		today = timezone.localdate()
		chatted_today = PrivateConversation.objects.filter(
			doctor=doctor.user,
			patient=request.user,
			updated_at__date=today,
		).exists()
		if not chatted_today:
			messages.warning(request, 'Ili urank doctor, lazima uwe umechat naye leo.')
			return redirect('doctor:detail', doctor_id=doctor.id)
		if DoctorRating.objects.filter(rater=request.user, doctor_profile=doctor, created_at__date=today).exists():
			messages.info(request, 'Tayari umerank doctor huyu leo.')
			return redirect('doctor:detail', doctor_id=doctor.id)

		try:
			score = int(request.POST.get('score') or 0)
		except ValueError:
			score = 0
		score = max(1, min(5, score))
		note = (request.POST.get('note') or '').strip()
		DoctorRating.objects.create(rater=request.user, doctor_profile=doctor, score=score, note=note)
		messages.success(request, 'Asante! Umerank doctor kikamilifu.')
		return redirect('doctor:detail', doctor_id=doctor.id)


class DoctorReportView(LoginRequiredMixin, View):
	def post(self, request, doctor_id, *args, **kwargs):
		doctor = get_object_or_404(DoctorProfile, pk=doctor_id)
		reason = (request.POST.get('reason') or '').strip()
		details = (request.POST.get('details') or '').strip()
		if not reason:
			messages.warning(request, 'Weka sababu ya report kwanza.')
			return redirect('doctor:detail', doctor_id=doctor.id)
		DoctorReport.objects.create(reporter=request.user, doctor_profile=doctor, reason=reason[:200], details=details)
		messages.success(request, 'Report imetumwa. Asante kwa taarifa.')
		return redirect('doctor:detail', doctor_id=doctor.id)


class DoctorRegistrationView(View):
	template_name = 'doctor/register.html'

	def get(self, request, *args, **kwargs):
		return render(request, self.template_name, {'form': DoctorRegistrationForm()})

	def post(self, request, *args, **kwargs):
		form = DoctorRegistrationForm(request.POST, request.FILES)
		if form.is_valid():
			form.save()
			messages.success(request, 'Doctor registration imewasilishwa. Admin atakagua na kuthibitisha account yako.')
			return redirect('users:login')
		messages.error(request, 'Doctor registration haijakamilika. Tafadhali rekebisha makosa.')
		return render(request, self.template_name, {'form': form})


class DoctorApprovalDashboardView(AdminRequiredMixin, View):
	template_name = 'doctor/approval_dashboard.html'

	def get(self, request, *args, **kwargs):
		requests = DoctorVerificationRequest.objects.select_related('doctor_profile__user', 'reviewed_by').prefetch_related('documents')
		return render(request, self.template_name, {'requests': requests})


class ReviewDoctorRequestView(AdminRequiredMixin, View):
	template_name = 'doctor/review_request.html'

	def get(self, request, request_id, *args, **kwargs):
		verification_request = get_object_or_404(
			DoctorVerificationRequest.objects.select_related('doctor_profile__user', 'reviewed_by').prefetch_related('documents'),
			pk=request_id,
		)
		return render(request, self.template_name, {'verification_request': verification_request})

	def post(self, request, request_id, *args, **kwargs):
		verification_request = get_object_or_404(DoctorVerificationRequest, pk=request_id)
		action = request.POST.get('action')
		notes = (request.POST.get('review_notes') or '').strip()

		if action == 'approve':
			verification_request.mark_approved(request.user, notes)
			messages.success(request, 'Doctor amethibitishwa kikamilifu.')
		elif action == 'reject':
			verification_request.mark_rejected(request.user, notes)
			messages.warning(request, 'Doctor request imekataliwa.')
		else:
			messages.error(request, 'Action haijatambulika.')

		return redirect('doctor:approval_dashboard')


# ─────────────────────────────────────────────────────────────────────────────
# PATIENT LOG SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

def _require_verified_doctor(request):
	"""Return the doctor's DoctorProfile or None."""
	profile = getattr(request.user, 'doctor_profile', None)
	return profile if (profile and profile.verified) else None


class DoctorPatientsView(LoginRequiredMixin, View):
	"""Verified doctor sees all patients they've ever chatted with."""
	template_name = 'doctor/patients.html'

	def get(self, request, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu wanaweza kuona orodha ya wagonjwa.')
			return redirect('doctor:hub')

		conversations = PrivateConversation.objects.filter(
			doctor=request.user,
		).select_related('patient').order_by('-updated_at')

		# Unique patients with their last-conversation time and any pending logs
		seen = set()
		patients = []
		for conv in conversations:
			if conv.patient_id not in seen:
				seen.add(conv.patient_id)
				active_logs = PatientLog.objects.filter(
					doctor=request.user, patient=conv.patient, is_active=True,
				).count()
				conv.patient.active_logs = active_logs
				conv.patient.last_chat = conv.updated_at
				conv.patient.conversation_id = conv.id
				patients.append(conv.patient)

		return render(request, self.template_name, {
			'patients': patients,
			'doctor_profile': doctor_profile,
		})


class DoctorPatientDetailView(LoginRequiredMixin, View):
	"""Doctor sees one patient profile, all forms and submitted logs."""
	template_name = 'doctor/patient_detail.html'

	def get(self, request, patient_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')

		patient = get_object_or_404(User, pk=patient_id)
		conversation = PrivateConversation.objects.filter(
			doctor=request.user, patient=patient
		).order_by('-updated_at').first()
		if not conversation:
			messages.error(request, 'Haujawahi kuzungumza na mtumiaji huyu.')
			return redirect('doctor:patients')

		logs = PatientLog.objects.filter(
			doctor=request.user,
			patient=patient,
		).prefetch_related('fields').order_by('-created_at')

		entries = PatientLogEntry.objects.filter(
			log__doctor=request.user,
			log__patient=patient,
		).select_related('log').order_by('-submitted_at')

		return render(request, self.template_name, {
			'doctor_profile': doctor_profile,
			'patient': patient,
			'conversation': conversation,
			'logs': logs,
			'entries': entries,
		})


class CreatePatientLogView(LoginRequiredMixin, View):
	"""Doctor builds and saves a custom log form for a specific patient."""
	template_name = 'doctor/create_patient_log.html'

	def get(self, request, patient_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')
		patient = get_object_or_404(User, pk=patient_id)
		# Ensure they've chatted
		if not PrivateConversation.objects.filter(doctor=request.user, patient=patient).exists():
			messages.error(request, 'Haujawahi kuzungumza na mtumiaji huyu.')
			return redirect('doctor:patients')
		existing_logs = PatientLog.objects.filter(doctor=request.user, patient=patient).prefetch_related('fields')
		return render(request, self.template_name, {
			'patient': patient,
			'existing_logs': existing_logs,
			'doctor_profile': doctor_profile,
			'metadata_choices': PatientLog.META_CHOICES,
		})

	def post(self, request, patient_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')
		patient = get_object_or_404(User, pk=patient_id)

		title = (request.POST.get('title') or '').strip()
		description = (request.POST.get('description') or '').strip()
		frequency = (request.POST.get('frequency') or '').strip()
		selected_metadata = request.POST.getlist('metadata_fields')
		allowed_meta = {c[0] for c in PatientLog.META_CHOICES}
		metadata_fields = [m for m in selected_metadata if m in allowed_meta]
		if not title:
			messages.error(request, 'Weka kichwa cha log form.')
			return redirect('doctor:create_patient_log', patient_id=patient.id)

		log = PatientLog.objects.create(
			doctor=request.user,
			patient=patient,
			title=title,
			description=description,
			frequency=frequency,
			is_active=True,
			is_sent=False,
			metadata_fields=metadata_fields,
		)

		# Dynamic fields: field_label_N, field_type_N, field_placeholder_N, field_required_N, field_options_N
		field_labels = request.POST.getlist('field_label')
		field_types = request.POST.getlist('field_type')
		field_placeholders = request.POST.getlist('field_placeholder')
		field_required_flags = request.POST.getlist('field_required')
		field_options_list = request.POST.getlist('field_options')

		valid_types = {f[0] for f in PatientLogField.FIELD_TYPE_CHOICES}
		for idx, label in enumerate(field_labels):
			label = label.strip()
			if not label:
				continue
			ftype = field_types[idx] if idx < len(field_types) else PatientLogField.FIELD_TEXT
			if ftype not in valid_types:
				ftype = PatientLogField.FIELD_TEXT
			placeholder = (field_placeholders[idx] if idx < len(field_placeholders) else '').strip()
			required = str(field_required_flags[idx]).lower() == 'on' if idx < len(field_required_flags) else False
			raw_options = (field_options_list[idx] if idx < len(field_options_list) else '').strip()
			options = [o.strip() for o in raw_options.split(',') if o.strip()] if raw_options else []
			PatientLogField.objects.create(
				log=log,
				field_label=label,
				field_type=ftype,
				placeholder=placeholder,
				required=required,
				options=options,
				order=idx,
			)

		messages.success(request, f'Log form "{title}" imetengenezwa. Unaweza sasa uitume kwa mgonjwa.')
		return redirect('doctor:patient_log_detail', log_id=log.id)


class EditPatientLogView(LoginRequiredMixin, View):
	"""Doctor edits an existing log form (including those already sent)."""
	template_name = 'doctor/create_patient_log.html'

	def get(self, request, log_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')

		log = get_object_or_404(
			PatientLog.objects.prefetch_related('fields'),
			pk=log_id,
			doctor=request.user,
		)
		existing_logs = PatientLog.objects.filter(
			doctor=request.user,
			patient=log.patient,
		).prefetch_related('fields')
		return render(request, self.template_name, {
			'patient': log.patient,
			'existing_logs': existing_logs,
			'doctor_profile': doctor_profile,
			'edit_log': log,
			'metadata_choices': PatientLog.META_CHOICES,
		})

	def post(self, request, log_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')

		log = get_object_or_404(PatientLog, pk=log_id, doctor=request.user)
		title = (request.POST.get('title') or '').strip()
		description = (request.POST.get('description') or '').strip()
		frequency = (request.POST.get('frequency') or '').strip()
		selected_metadata = request.POST.getlist('metadata_fields')
		allowed_meta = {c[0] for c in PatientLog.META_CHOICES}
		metadata_fields = [m for m in selected_metadata if m in allowed_meta]
		if not title:
			messages.error(request, 'Weka kichwa cha log form.')
			return redirect('doctor:edit_patient_log', log_id=log.id)

		log.title = title
		log.description = description
		log.frequency = frequency
		log.metadata_fields = metadata_fields
		log.save(update_fields=['title', 'description', 'frequency', 'metadata_fields', 'updated_at'])

		field_labels = request.POST.getlist('field_label')
		field_types = request.POST.getlist('field_type')
		field_placeholders = request.POST.getlist('field_placeholder')
		field_required_flags = request.POST.getlist('field_required')
		field_options_list = request.POST.getlist('field_options')

		# Rebuild fields using submitted structure
		log.fields.all().delete()
		valid_types = {f[0] for f in PatientLogField.FIELD_TYPE_CHOICES}
		for idx, label in enumerate(field_labels):
			label = label.strip()
			if not label:
				continue
			ftype = field_types[idx] if idx < len(field_types) else PatientLogField.FIELD_TEXT
			if ftype not in valid_types:
				ftype = PatientLogField.FIELD_TEXT
			placeholder = (field_placeholders[idx] if idx < len(field_placeholders) else '').strip()
			required = str(field_required_flags[idx]).lower() == 'on' if idx < len(field_required_flags) else False
			raw_options = (field_options_list[idx] if idx < len(field_options_list) else '').strip()
			options = [o.strip() for o in raw_options.split(',') if o.strip()] if raw_options else []
			PatientLogField.objects.create(
				log=log,
				field_label=label,
				field_type=ftype,
				placeholder=placeholder,
				required=required,
				options=options,
				order=idx,
			)

		messages.success(request, f'Log form "{log.title}" imehaririwa kikamilifu.')
		return redirect('doctor:patient_detail', patient_id=log.patient_id)


class DeletePatientLogView(LoginRequiredMixin, View):
	"""Doctor deletes a patient log and sends a private message notification to patient."""

	def post(self, request, log_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')

		log = get_object_or_404(PatientLog, pk=log_id, doctor=request.user)
		patient = log.patient
		log_title = log.title

		conversation = PrivateConversation.objects.filter(
			doctor=request.user,
			patient=patient,
		).order_by('-updated_at').first()
		if not conversation:
			conversation = PrivateConversation.objects.create(
				doctor=request.user,
				patient=patient,
				subject='Doctor Update',
			)

		from chats.models import PrivateMessage
		PrivateMessage.objects.create(
			conversation=conversation,
			sender=request.user,
			content=f'Daktari amefuta form ya log: "{log_title}". Tafadhali subiri maelekezo mapya au wasiliana kupitia chat hii.',
		)

		log.delete()
		messages.success(request, f'Log form "{log_title}" imefutwa na mgonjwa amepewa taarifa kwenye chat.')
		return redirect('doctor:patient_detail', patient_id=patient.id)


class SendPatientLogView(LoginRequiredMixin, View):
	"""Doctor marks a log as sent — patient will now see it in their nav."""
	def post(self, request, log_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')
		log = get_object_or_404(PatientLog, pk=log_id, doctor=request.user)
		log.is_sent = True
		log.save(update_fields=['is_sent'])
		messages.success(request, f'Log form "{log.title}" imetumwa kwa {log.patient.username}. Watapata nav mpya ya Log.')
		return redirect('doctor:patient_log_detail', log_id=log.id)


class PatientLogDetailView(LoginRequiredMixin, View):
	"""Doctor views a log form they created: fields + all entries from the patient."""
	template_name = 'doctor/patient_log_detail.html'

	def get(self, request, log_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')
		log = get_object_or_404(
			PatientLog.objects.prefetch_related('fields', 'entries__submitted_by'),
			pk=log_id, doctor=request.user,
		)
		conversation = PrivateConversation.objects.filter(
			doctor=request.user, patient=log.patient
		).order_by('-updated_at').first()
		return render(request, self.template_name, {
			'log': log,
			'doctor_profile': doctor_profile,
			'conversation': conversation,
		})


class PatientEntryDetailView(LoginRequiredMixin, View):
	"""Doctor sees full details of one specific submitted patient entry."""
	template_name = 'doctor/patient_entry_detail.html'

	def get(self, request, entry_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')

		entry = get_object_or_404(
			PatientLogEntry.objects.select_related('log', 'submitted_by'),
			pk=entry_id,
			log__doctor=request.user,
		)
		fields = entry.log.fields.all()

		formatted_values = []
		for field in fields:
			value = entry.data.get(str(field.id), '')
			if field.field_type == PatientLogField.FIELD_CHECKBOX:
				value = 'Ndiyo' if value else 'Hapana'
			elif value in (None, ''):
				value = '—'
			formatted_values.append((field, value))

		meta_label_map = dict(PatientLog.META_CHOICES)
		formatted_metadata = []
		for key in (entry.log.metadata_fields or []):
			label = meta_label_map.get(key, key)
			raw_meta = (entry.metadata or {}).get(key)
			value = str(raw_meta) if raw_meta not in (None, '') else '—'
			formatted_metadata.append((label, value))

		conversation = PrivateConversation.objects.filter(
			doctor=request.user,
			patient=entry.log.patient,
		).order_by('-updated_at').first()

		return render(request, self.template_name, {
			'entry': entry,
			'formatted_values': formatted_values,
			'formatted_metadata': formatted_metadata,
			'conversation': conversation,
			'doctor_profile': doctor_profile,
		})


class PatientAnalysisView(LoginRequiredMixin, View):
	"""Doctor sees graphical trend + AI-style analysis for one patient based on submitted logs."""
	template_name = 'doctor/patient_analysis.html'

	def get(self, request, patient_id, *args, **kwargs):
		doctor_profile = _require_verified_doctor(request)
		if not doctor_profile:
			messages.error(request, 'Ni madaktari waliothibitishwa tu.')
			return redirect('doctor:hub')

		patient = get_object_or_404(User, pk=patient_id)
		conversation = PrivateConversation.objects.filter(
			doctor=request.user,
			patient=patient,
		).order_by('-updated_at').first()
		if not conversation:
			messages.error(request, 'Haujawahi kuzungumza na mtumiaji huyu.')
			return redirect('doctor:patients')

		logs = PatientLog.objects.filter(
			doctor=request.user,
			patient=patient,
		).prefetch_related('fields')

		entries = list(
			PatientLogEntry.objects.filter(
				log__doctor=request.user,
				log__patient=patient,
			).select_related('log').order_by('submitted_at')
		)

		all_fields = list(
			PatientLogField.objects.filter(
				log__doctor=request.user,
				log__patient=patient,
			).select_related('log').order_by('log__created_at', 'order', 'id')
		)

		meta_label_map = dict(PatientLog.META_CHOICES)
		selected_metadata_keys = []
		seen_meta = set()
		for log in logs:
			for key in (log.metadata_fields or []):
				if key in meta_label_map and key not in seen_meta:
					seen_meta.add(key)
					selected_metadata_keys.append(key)
		selected_metadata_columns = [
			{'key': key, 'label': meta_label_map.get(key, key)}
			for key in selected_metadata_keys
		]

		# Core KPI metrics
		entry_count = len(entries)
		active_days = len({e.submitted_at.date() for e in entries}) if entries else 0
		span_days = 0
		if entries:
			span_days = (entries[-1].submitted_at.date() - entries[0].submitted_at.date()).days + 1
			span_days = max(1, span_days)
		adherence_pct = round((active_days / span_days) * 100, 1) if span_days else 0.0
		avg_entries_per_day = round(entry_count / span_days, 2) if span_days else 0.0

		required_fields = [f for f in all_fields if f.required]
		required_total = len(required_fields)
		required_checks = 0
		required_filled = 0
		for entry in entries:
			for field in required_fields:
				required_checks += 1
				raw = entry.data.get(str(field.id))
				is_filled = False
				if field.field_type == PatientLogField.FIELD_CHECKBOX:
					is_filled = raw is not None
				else:
					is_filled = raw not in (None, '')
				if is_filled:
					required_filled += 1
		completion_pct = round((required_filled / required_checks) * 100, 1) if required_checks else 100.0

		labels = [entry.submitted_at.strftime('%d %b %H:%M') for entry in entries]
		field_map = {}
		for log in logs:
			for field in log.fields.all():
				field_map[str(field.id)] = field

		palette = ['#2F6B3F', '#7FB77E', '#F59E0B', '#2563EB', '#7C3AED', '#DB2777', '#0891B2', '#DC2626']
		datasets = []
		field_charts = []
		insights = []
		field_summaries = []
		risk_flags = []
		color_idx = 0

		for field_id, field in field_map.items():
			if field.field_type not in {PatientLogField.FIELD_NUMBER, PatientLogField.FIELD_SCALE, PatientLogField.FIELD_CHECKBOX}:
				continue

			values = []
			numeric_points = []
			for entry in entries:
				raw = entry.data.get(field_id)
				val = None
				if field.field_type == PatientLogField.FIELD_CHECKBOX:
					val = 1 if raw else 0
				else:
					try:
						val = float(raw) if raw not in (None, '') else None
					except (TypeError, ValueError):
						val = None
				values.append(val)
				if val is not None:
					numeric_points.append(val)

			if not any(v is not None for v in values):
				continue

			color = palette[color_idx % len(palette)]
			color_idx += 1
			datasets.append({
				'label': f'{field.field_label} ({field.get_field_type_display()})',
				'data': values,
				'borderColor': color,
				'backgroundColor': color,
				'spanGaps': True,
				'tension': 0.25,
			})

			field_charts.append({
				'field_label': field.field_label,
				'field_type': field.get_field_type_display(),
				'log_title': field.log.title,
				'labels': labels,
				'data': values,
				'color': color,
			})

			if len(numeric_points) >= 2:
				first_val = numeric_points[0]
				last_val = numeric_points[-1]
				delta = last_val - first_val
				prev_val = numeric_points[-2]
				if abs(delta) < 0.01:
					trend = 'imebaki stable'
					trend_short = 'stable'
				elif delta > 0:
					trend = 'imekuwa ikiongezeka'
					trend_short = 'up'
				else:
					trend = 'imekuwa ikishuka'
					trend_short = 'down'
				avg = sum(numeric_points) / len(numeric_points)
				volatility = statistics.pstdev(numeric_points) if len(numeric_points) > 1 else 0.0
				insights.append(
					f'{field.field_label}: trend {trend}, wastani {avg:.2f}, mabadiliko {delta:+.2f}.'
				)

				field_summaries.append({
					'label': field.field_label,
					'log_title': field.log.title,
					'field_type': field.get_field_type_display(),
					'latest': round(last_val, 2),
					'average': round(avg, 2),
					'delta': round(delta, 2),
					'volatility': round(volatility, 2),
					'trend': trend_short,
				})

				# Heuristic clinical-risk style alerts
				if field.field_type == PatientLogField.FIELD_SCALE and last_val <= 3:
					risk_flags.append(f'ALERT: {field.field_label} iko chini ({last_val}/10) kwenye entry ya mwisho.')
				if abs(last_val - prev_val) >= 3:
					risk_flags.append(f'ALERT: Mabadiliko makubwa kwenye {field.field_label} ({prev_val:.1f} → {last_val:.1f}).')
			elif len(numeric_points) == 1:
				field_summaries.append({
					'label': field.field_label,
					'log_title': field.log.title,
					'field_type': field.get_field_type_display(),
					'latest': round(numeric_points[0], 2),
					'average': round(numeric_points[0], 2),
					'delta': 0,
					'volatility': 0,
					'trend': 'stable',
				})

		if not risk_flags:
			risk_flags.append('Hakuna red-flag kubwa iliyoonekana kwa heuristics za sasa.')

		if not insights:
			insights.append('Hakuna data ya kutosha kufanya trend analysis ya kina kwa sasa.')

		analysis_notes = []
		if len(entries) >= 3:
			analysis_notes.append('AI analysis: Patient ana consistency nzuri kwenye kujaza logs.')
		elif len(entries) > 0:
			analysis_notes.append('AI analysis: Data ipo lakini bado ni ndogo; endelea kukusanya entries zaidi kwa maamuzi sahihi.')
		else:
			analysis_notes.append('AI analysis: Bado hakuna submissions; mtie moyo patient aanze kujaza form.')

		if datasets:
			analysis_notes.append('Tumia trend zilizo kwenye graph kuamua kama kuna haja ya follow-up chat au kubadilisha form.')

		# Supporting dashboard charts (daily volume, weekday, completion trend)
		daily_counter = {}
		daily_completion = {}
		for entry in entries:
			day_key = entry.submitted_at.date().isoformat()
			daily_counter[day_key] = daily_counter.get(day_key, 0) + 1
			if required_fields:
				filled = 0
				for field in required_fields:
					raw = entry.data.get(str(field.id))
					if field.field_type == PatientLogField.FIELD_CHECKBOX:
						if raw is not None:
							filled += 1
					elif raw not in (None, ''):
						filled += 1
				rate = (filled / len(required_fields)) * 100
				daily_completion.setdefault(day_key, []).append(rate)

		daily_labels = sorted(daily_counter.keys())
		daily_counts = [daily_counter[k] for k in daily_labels]
		completion_labels = sorted(daily_completion.keys())
		completion_values = [round(sum(v) / len(v), 2) for k, v in sorted(daily_completion.items())]

		weekday_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
		weekday_counts = [0] * 7
		for entry in entries:
			weekday_counts[entry.submitted_at.weekday()] += 1

		kpi = {
			'entry_count': entry_count,
			'active_days': active_days,
			'span_days': span_days,
			'adherence_pct': adherence_pct,
			'avg_entries_per_day': avg_entries_per_day,
			'completion_pct': completion_pct,
		}

		# Full table data per day (includes text/textarea/select/number/checkbox/scale)
		entries_desc = sorted(entries, key=lambda e: e.submitted_at, reverse=True)
		daily_input_tables = []
		bucket_map = {}
		for entry in entries_desc:
			day = entry.submitted_at.date()
			if day not in bucket_map:
				bucket = {
					'date': day,
					'rows': [],
				}
				bucket_map[day] = bucket
				daily_input_tables.append(bucket)

			row_values = []
			for field in all_fields:
				raw = entry.data.get(str(field.id))
				if raw in (None, ''):
					value = '—'
				elif field.field_type == PatientLogField.FIELD_CHECKBOX:
					value = 'Ndiyo' if raw else 'Hapana'
				elif field.field_type == PatientLogField.FIELD_SCALE:
					value = f'{raw}/10'
				elif isinstance(raw, list):
					value = ', '.join(str(item) for item in raw) if raw else '—'
				else:
					value = str(raw)
				row_values.append(value)

			meta_values = []
			for meta_key in selected_metadata_keys:
				raw_meta = (entry.metadata or {}).get(meta_key)
				meta_values.append(str(raw_meta) if raw_meta not in (None, '') else '—')

			bucket_map[day]['rows'].append({
				'entry_id': entry.id,
				'log_title': entry.log.title,
				'submitted_at': entry.submitted_at,
				'values': row_values,
				'meta_values': meta_values,
			})

		return render(request, self.template_name, {
			'doctor_profile': doctor_profile,
			'patient': patient,
			'conversation': conversation,
			'logs': logs,
			'entries': entries,
			'chart_labels_json': json.dumps(labels),
			'chart_datasets_json': json.dumps(datasets),
			'field_charts_json': json.dumps(field_charts),
			'daily_volume_json': json.dumps({'labels': daily_labels, 'values': daily_counts}),
			'weekday_json': json.dumps({'labels': weekday_names, 'values': weekday_counts}),
			'completion_json': json.dumps({'labels': completion_labels, 'values': completion_values}),
			'kpi': kpi,
			'insights': insights,
			'analysis_notes': analysis_notes,
			'field_summaries': field_summaries,
			'risk_flags': risk_flags,
			'all_fields': all_fields,
			'selected_metadata_columns': selected_metadata_columns,
			'daily_input_tables': daily_input_tables,
		})


# ─── Patient-side views ───────────────────────────────────────────────────────

class MyPatientLogsView(LoginRequiredMixin, View):
	"""Patient sees all log forms assigned to them by their doctors."""
	template_name = 'doctor/my_patient_logs.html'

	def get(self, request, *args, **kwargs):
		logs = PatientLog.objects.filter(
			patient=request.user, is_active=True, is_sent=True,
		).select_related('doctor').prefetch_related('fields').order_by('-created_at')
		return render(request, self.template_name, {'logs': logs})


class PatientLogFillView(LoginRequiredMixin, View):
	"""Patient fills in and submits a single log entry."""
	template_name = 'doctor/patient_log_fill.html'

	def get(self, request, log_id, *args, **kwargs):
		log = get_object_or_404(
			PatientLog.objects.prefetch_related('fields'),
			pk=log_id, patient=request.user, is_active=True, is_sent=True,
		)
		recent_entries = log.entries.filter(submitted_by=request.user)[:5]
		return render(request, self.template_name, {
			'log': log,
			'recent_entries': recent_entries,
		})

	def post(self, request, log_id, *args, **kwargs):
		log = get_object_or_404(
			PatientLog.objects.prefetch_related('fields'),
			pk=log_id, patient=request.user, is_active=True, is_sent=True,
		)
		data = {}
		for field in log.fields.all():
			key = f'field_{field.id}'
			if field.field_type == PatientLogField.FIELD_CHECKBOX:
				data[str(field.id)] = request.POST.get(key) == 'on'
			else:
				value = (request.POST.get(key) or '').strip()
				if field.required and not value:
					messages.error(request, f'Tafadhali jaza: {field.field_label}')
					return redirect('doctor:patient_log_fill', log_id=log.id)
				data[str(field.id)] = value

		# Metadata capture based on doctor-selected options
		metadata = {}
		selected_meta = set(log.metadata_fields or [])
		now_local = timezone.localtime()
		if PatientLog.META_ENTRY_TIME in selected_meta:
			metadata[PatientLog.META_ENTRY_TIME] = now_local.strftime('%Y-%m-%d %H:%M:%S')
		if PatientLog.META_ENTRY_DAY in selected_meta:
			metadata[PatientLog.META_ENTRY_DAY] = now_local.strftime('%A')
		if PatientLog.META_PATIENT_REGION in selected_meta:
			persona = UserAIPersona.objects.filter(user=request.user).only('location_region').first()
			metadata[PatientLog.META_PATIENT_REGION] = (persona.location_region if persona and persona.location_region else 'Unknown')
		if PatientLog.META_PATIENT_GENDER in selected_meta:
			metadata[PatientLog.META_PATIENT_GENDER] = get_user_gender(request.user) or 'unknown'
		if PatientLog.META_DEVICE_TYPE in selected_meta:
			metadata[PatientLog.META_DEVICE_TYPE] = _detect_device_type(request)
		if PatientLog.META_IP_APPROX_LOCATION in selected_meta:
			country = request.META.get('HTTP_CF_IPCOUNTRY') or request.META.get('GEOIP_COUNTRY_CODE') or ''
			masked_ip = _mask_ip(_get_client_ip(request))
			metadata[PatientLog.META_IP_APPROX_LOCATION] = f'{country} {masked_ip}'.strip() if country else masked_ip
		if PatientLog.META_SESSION_SOURCE in selected_meta:
			metadata[PatientLog.META_SESSION_SOURCE] = _detect_session_source(request)

		PatientLogEntry.objects.create(log=log, submitted_by=request.user, data=data, metadata=metadata)
		messages.success(request, 'Taarifa yako imepokewa na daktari. Asante!')
		return redirect('doctor:my_patient_logs')
