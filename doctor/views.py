from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import DoctorRegistrationForm
from .models import DoctorVerificationRequest
from menstrual.models import DoctorProfile
from users.permissions import AdminRequiredMixin, is_admin, is_doctor
from users.utils import get_user_gender


class DoctorHubView(LoginRequiredMixin, View):
	template_name = 'doctor/hub.html'

	def get(self, request, *args, **kwargs):
		user_gender = get_user_gender(request.user)
		selected_gender = request.GET.get('gender')
		doctors = DoctorProfile.objects.select_related('user').order_by('-verified', 'user__username')
		if selected_gender in {'female', 'male'}:
			doctors = doctors.filter(gender=selected_gender)
		elif user_gender in {'female', 'male'}:
			doctors = doctors.filter(gender=user_gender)
		my_profile = DoctorProfile.objects.filter(user=request.user).first()
		pending_requests = DoctorVerificationRequest.objects.filter(status=DoctorVerificationRequest.STATUS_PENDING).count()
		current_filter = selected_gender if selected_gender in {'female', 'male'} else user_gender
		return render(
			request,
			self.template_name,
			{
				'doctors': doctors,
				'verified_count': doctors.filter(verified=True).count(),
				'my_doctor_profile': my_profile,
				'can_manage_doctors': is_admin(request.user),
				'is_doctor_account': is_doctor(request.user),
				'pending_requests': pending_requests,
				'user_gender': user_gender,
				'selected_doctor_gender': current_filter,
			},
		)


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
