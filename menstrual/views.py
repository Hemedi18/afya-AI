import json
from django import forms as django_forms
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, TemplateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from datetime import timedelta
from django.utils import timezone
from .models import MenstrualCycle, DailyLog, CommunityPost, DoctorProfile, DailyTip, Reminder, MenstrualUserSetting
from .forms import DailyLogForm, MenstrualCycleForm, MenstrualUserSettingForm, DailyTipForm
from AI_brain.services import generate_ai_text
from users.permissions import is_admin, is_doctor
from users.utils import get_user_gender
from .tasks import refresh_daily_tips_task


def _get_cycle_intervals(user_cycles):
    if len(user_cycles) < 2:
        return []
    return [
        (user_cycles[idx].start_date - user_cycles[idx - 1].start_date).days
        for idx in range(1, len(user_cycles))
    ]


def _build_cycle_ai_brief(all_logs, active_cycle, cycle_intervals=None):
    """
    Rule-based AI-style summary for dashboard personalization.
    Kept deterministic and fast so it can run on every request.
    """
    if not all_logs:
        return {
            'health_score': 75,
            'status': 'Inahitaji data zaidi',
            'status_color': 'warning',
            'alerts': ['Anza kwa kuweka log za kila siku kwa siku 5-7 ili AI ikujue vizuri.'],
            'emergency_alerts': [],
            'summary': 'Bado hakuna kumbukumbu za kutosha. AI itatoa uchambuzi sahihi zaidi ukianza kuweka rekodi kila siku.',
        }

    recent_logs = all_logs[-7:]
    avg_flow = sum(log.flow_intensity for log in recent_logs) / len(recent_logs)

    symptom_count = 0
    mood_count = 0
    for log in recent_logs:
        symptom_count += len(log.physical_symptoms or [])
        mood_count += len(log.emotional_changes or [])

    # Lightweight health score formula (0-100)
    score = 100
    score -= min(30, int(avg_flow * 4))
    score -= min(20, symptom_count * 2)
    score -= min(15, mood_count * 2)
    score = max(40, min(98, score))

    alerts = []
    if avg_flow >= 4:
        alerts.append('Kiwango cha damu kimekuwa juu siku za karibuni. Endelea kunywa maji na fuatilia uchovu.')
    if symptom_count >= 10:
        alerts.append('Dalili zimeongezeka wiki hii. Pumzika zaidi na zingatia lishe yenye madini ya chuma.')
    if mood_count >= 6:
        alerts.append('Mabadiliko ya hisia yanaonekana mara kwa mara; jaribu usingizi wa kutosha na mazoezi mepesi.')

    if not alerts:
        alerts.append('Mwelekeo wako unaonekana tulivu. Endelea na tabia nzuri za usingizi, maji na lishe.')

    emergency_alerts = []
    heavy_days = sum(1 for log in recent_logs if log.flow_intensity >= 4)
    if heavy_days >= 4:
        emergency_alerts.append('Kuna heavy bleeding kwa siku nyingi mfululizo. Inashauriwa kushauriana na daktari mapema.')

    if active_cycle and active_cycle.elapsed_days > 10:
        emergency_alerts.append('Mzunguko wa sasa umevuka siku 10. Fuatilia kwa karibu na wasiliana na daktari kama hali inaendelea.')

    cycle_intervals = cycle_intervals or []
    irregular_cycles = sum(1 for days in cycle_intervals if days < 21 or days > 45)
    if irregular_cycles >= 2:
        emergency_alerts.append('Mizunguko ya karibuni inaonekana irregular mara kadhaa. Inashauriwa kufanya uchunguzi wa homoni kwa ushauri wa daktari.')

    if score >= 85:
        status = 'Imara'
        status_color = 'success'
    elif score >= 70:
        status = 'Ya Kati'
        status_color = 'warning'
    else:
        status = 'Inahitaji uangalizi'
        status_color = 'danger'

    summary = (
        f"Kwa uchambuzi wa siku 7 zilizopita, mzunguko wako unaonyesha wastani wa flow {avg_flow:.1f}/5. "
        f"AI inapendekeza kuendelea na ufuatiliaji wa kila siku ili kuboresha utabiri wa kipindi kijacho."
    )

    return {
        'health_score': score,
        'status': status,
        'status_color': status_color,
        'alerts': alerts,
        'emergency_alerts': emergency_alerts,
        'cycle_irregular': irregular_cycles >= 2,
        'summary': summary,
    }


def _build_ai_prediction_note(active_cycle, all_logs, ai_dashboard=None, adaptive_cycle_length=None):
    if not active_cycle:
        return "Anza kwa kuweka mzunguko wako wa kwanza ili AI itoe prediction binafsi."

    if len(all_logs) < 3:
        return "AI inahitaji angalau logs 3 ili prediction iwe sahihi zaidi. Endelea kuweka data ya kila siku."

    ai_dashboard = ai_dashboard or {}
    if ai_dashboard.get('emergency_alerts'):
        cycle_length_text = adaptive_cycle_length or active_cycle.cycle_length
        return (
            f"Prediction ya sasa inaonyesha pattern ya karibu siku {cycle_length_text}, lakini kuna ishara zinazohitaji ufuatiliaji wa karibu. "
            "Kwa sasa tumia prediction hii kama mwongozo wa muda tu, endelea kuweka logs kila siku na wasiliana na daktari ikiwa mabadiliko yanaendelea au yanaongezeka."
        )

    recent = all_logs[-5:]
    flow_avg = round(sum(log.flow_intensity for log in recent) / len(recent), 1)
    symptoms = sorted({s for log in recent for s in (log.physical_symptoms or [])})
    symptom_text = ', '.join(symptoms[:5]) if symptoms else 'hakuna dalili kubwa'
    cycle_length_text = adaptive_cycle_length or active_cycle.cycle_length

    prompt = (
        "Toa uchambuzi mfupi sana kwa Kiswahili wa mzunguko wa mwanamke kwa lugha rahisi, usitoe hofu. "
        f"Cycle length: {cycle_length_text}, period duration: {active_cycle.period_duration}, "
        f"average recent flow: {flow_avg}/5, symptoms: {symptom_text}. "
        "Usiseme kuna emergency au irregularity kama hakuna alert. Toa sentensi 2: prediction + hatua ya kujitunza."
    )
    fallback = (
        f"Kwa data ya hivi karibuni, mzunguko wako unaonekana kufuata pattern ya takriban siku {cycle_length_text}. "
        "Endelea na maji ya kutosha, usingizi mzuri, na fuatilia dalili zisizo za kawaida mapema."
    )
    return generate_ai_text(prompt, fallback)


def _can_submit_tip(user):
    if is_admin(user):
        return True
    doctor_profile = getattr(user, 'doctor_profile', None)
    return bool(is_doctor(user) and doctor_profile and doctor_profile.verified)


def _get_dashboard_tip_cards():
    today = timezone.localdate()
    tips = list(DailyTip.objects.filter(date_created=today).order_by('-id')[:5])
    if len(tips) < 5:
        refresh_daily_tips_task(limit=5)
        tips = list(DailyTip.objects.filter(date_created=today).order_by('-id')[:5])

    if len(tips) < 5:
        latest_fallback = list(DailyTip.objects.all().order_by('-date_created', '-id')[:5])
        return latest_fallback
    return tips


class FemaleMenstrualOnlyMixin:
    def dispatch(self, request, *args, **kwargs):
        gender = get_user_gender(request.user)
        if gender == 'male':
            messages.info(request, 'Hii sehemu ni ya afya ya hedhi kwa wanawake. Umeelekezwa kwenye dashboard yako.')
            return redirect('main:male_dashboard')
        if gender != 'female':
            messages.warning(request, 'Kamilisha profile yako (gender) kwanza ili kupata huduma sahihi.')
            return redirect('users:onboarding', step=1)
        return super().dispatch(request, *args, **kwargs)

class MenstrualDashboardView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, TemplateView):
    template_name = 'menstrual/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().date()
        context['today'] = today

        # Optimization: Use prefetch_related to get all logs in one query
        # and index lookup is now faster due to model changes.
        active_cycle = MenstrualCycle.objects.filter(
            user=self.request.user, is_active=True
        ).prefetch_related('daily_logs').first()
        
        context['active_cycle'] = active_cycle
        context['tips'] = _get_dashboard_tip_cards()
        context['can_submit_tip'] = _can_submit_tip(self.request.user)
        context['myth_busting_cards'] = [
            {
                'title': 'Myth: Hedhi ni uchafu',
                'fact': 'Fact: Hedhi ni mchakato wa kawaida wa mwili wa mwanamke, si uchafu wala laana.',
            },
            {
                'title': 'Myth: Maumivu makali ni kawaida kwa wote',
                'fact': 'Fact: Maumivu makali sana yanayorudia yanahitaji ushauri wa daktari mapema.',
            },
            {
                'title': 'Myth: Ukiwa na period huwezi kufanya chochote',
                'fact': 'Fact: Unaweza kuendelea na shughuli nyingi ukiwa na maandalizi na self-care sahihi.',
            },
        ]
        settings_obj, _ = MenstrualUserSetting.objects.get_or_create(user=self.request.user)
        context['menstrual_settings'] = settings_obj

        user_cycles = list(MenstrualCycle.objects.filter(user=self.request.user).order_by('start_date').only('start_date'))
        cycle_intervals = _get_cycle_intervals(user_cycles)
        adaptive_cycle_length = None
        if cycle_intervals:
            valid_intervals = [days for days in cycle_intervals if 21 <= days <= 45]
            if valid_intervals:
                adaptive_cycle_length = round(sum(valid_intervals) / len(valid_intervals))
        context['adaptive_cycle_length'] = adaptive_cycle_length
        
        if active_cycle:
            # Optimization: Sort the prefetched logs in Python to avoid extra DB hits
            all_logs = sorted(active_cycle.daily_logs.all(), key=lambda x: x.date)
            context['logs_chronological'] = all_logs
            context['logs'] = all_logs[::-1] # Reverse for history table
            
            # Tafuta log ya leo ili tuweze kuitoa kwa ajili ya kuhariri (Editing)
            today_log = next((log for log in all_logs if log.date == today), None)
            context['today_log'] = today_log

            configured_cycle_length = active_cycle.cycle_length or max(1, (active_cycle.expected_end_date - active_cycle.start_date).days + 1)
            cycle_length = adaptive_cycle_length or configured_cycle_length
            context['cycle_length'] = cycle_length
            context['period_duration'] = active_cycle.period_duration
            
            context['chart_data_json'] = json.dumps({
                'labels': [log.date.strftime('%d %b') for log in all_logs],
                'values': [log.flow_intensity for log in all_logs]
            })
            # AI-friendly prediction using user-configured cycle length
            predicted_next_period = active_cycle.start_date + timedelta(days=cycle_length)
            context['predicted_next_period'] = predicted_next_period
            context['days_to_next_period'] = (predicted_next_period - today).days
            context['prediction_mode'] = 'AI Adaptive' if adaptive_cycle_length else 'Configured'

            # Ovulation usually ~14 days before next period
            ovulation_date = predicted_next_period - timedelta(days=14)
            fertile_start = ovulation_date - timedelta(days=5)
            fertile_end = ovulation_date + timedelta(days=1)
            context['ovulation_date'] = ovulation_date
            context['fertile_start'] = fertile_start
            context['fertile_end'] = fertile_end
            
            # Summary of symptoms from the last 7 days
            seven_days_ago = timezone.now().date() - timedelta(days=7)
            # Optimization: Filter the prefetched list in Python to avoid an extra DB hit
            recent_logs = [log for log in all_logs if log.date >= seven_days_ago]
            
            symptom_summary = set()
            for log in recent_logs:
                symptom_summary.update(log.physical_symptoms or [])
                symptom_summary.update(log.emotional_changes or [])
            context['recent_symptoms_summary'] = sorted(list(symptom_summary))

            context['ai_dashboard'] = _build_cycle_ai_brief(all_logs, active_cycle, cycle_intervals=cycle_intervals)
            context['ai_prediction_note'] = _build_ai_prediction_note(
                active_cycle,
                all_logs,
                ai_dashboard=context['ai_dashboard'],
                adaptive_cycle_length=adaptive_cycle_length,
            )
        else:
            context['logs_chronological'] = []
            context['logs'] = []
            context['today_log'] = None
            context['cycle_length'] = 28
            context['period_duration'] = 5
            context['days_to_next_period'] = None
            context['recent_symptoms_summary'] = []
            context['ai_dashboard'] = _build_cycle_ai_brief([], None)
            context['prediction_mode'] = 'Configured'
            context['ai_prediction_note'] = _build_ai_prediction_note(None, [])
            
        return context


class MenstrualSettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'menstrual/settings.html'

    def get(self, request, *args, **kwargs):
        settings_obj, _ = MenstrualUserSetting.objects.get_or_create(user=request.user)
        form = MenstrualUserSettingForm(instance=settings_obj)
        return render(request, self.template_name, {'form': form})

    def post(self, request, *args, **kwargs):
        settings_obj, _ = MenstrualUserSetting.objects.get_or_create(user=request.user)
        form = MenstrualUserSettingForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings zako zimehifadhiwa.')
            return redirect('menstrual:settings')
        messages.error(request, 'Imeshindikana kuhifadhi settings. Angalia makosa.')
        return render(request, self.template_name, {'form': form})


class DailyTipCreateView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, TemplateView):
    template_name = 'menstrual/tip_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not _can_submit_tip(request.user):
            messages.error(request, 'Ni admin au daktari aliyethibitishwa pekee anayeweza kuweka tips.')
            return redirect('menstrual:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = DailyTipForm(initial={'source': 'DOCTOR' if not is_admin(request.user) else 'WEB'})
        if not is_admin(request.user):
            form.fields['source'].widget = django_forms.HiddenInput()
        return render(request, self.template_name, {'form': form, 'is_admin_user': is_admin(request.user)})

    def post(self, request, *args, **kwargs):
        form = DailyTipForm(request.POST)
        if not is_admin(request.user):
            form.fields['source'].widget = django_forms.HiddenInput()
        if form.is_valid():
            tip = form.save(commit=False)
            if not is_admin(request.user):
                tip.source = 'DOCTOR'
            tip.ui_structure = tip.ui_structure or {
                'accent': '#c9184a',
                'accent_soft': 'rgba(201,24,74,0.12)',
                'glow': 'rgba(201,24,74,0.20)',
            }
            tip.save()
            messages.success(request, 'Tip mpya imehifadhiwa kwa mafanikio.')
            return redirect('menstrual:dashboard')
        messages.error(request, 'Tip haijahifadhiwa. Tafadhali rekebisha makosa.')
        return render(request, self.template_name, {'form': form, 'is_admin_user': is_admin(request.user)})


class MenstrualReportView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, TemplateView):
    template_name = 'menstrual/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_cycle = MenstrualCycle.objects.filter(
            user=self.request.user, is_active=True
        ).prefetch_related('daily_logs').first()

        if not active_cycle:
            context['has_data'] = False
            context['report_chart_json'] = json.dumps({'labels': [], 'flow': [], 'symptoms': []})
            context['report_summary'] = "Bado hakuna data ya mzunguko. Anza kwa kuweka log kila siku."
            return context

        logs = sorted(active_cycle.daily_logs.all(), key=lambda x: x.date)
        context['has_data'] = bool(logs)

        labels = [log.date.strftime('%d %b') for log in logs]
        flow = [log.flow_intensity for log in logs]
        symptoms_count = [len(log.physical_symptoms or []) for log in logs]

        context['report_chart_json'] = json.dumps({
            'labels': labels,
            'flow': flow,
            'symptoms': symptoms_count,
        })

        avg_flow = round((sum(flow) / len(flow)), 1) if flow else 0
        total_days = len(logs)
        summary = (
            f"Ripoti ya AI: umeweka kumbukumbu kwa siku {total_days}. "
            f"Wastani wa flow ni {avg_flow}/5. "
            "Trend inaonekana kwenye grafu hapa chini na unaweza kushare mafanikio yako kwenye jamii."
        )
        context['report_summary'] = summary
        return context

class MenstrualCycleCreateView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, CreateView):
    model = MenstrualCycle
    form_class = MenstrualCycleForm
    template_name = 'menstrual/cycle_form.html'
    success_url = reverse_lazy('menstrual:dashboard')

    def form_valid(self, form):
        # Deactivate any existing active cycles for this user
        MenstrualCycle.objects.filter(user=self.request.user, is_active=True).update(is_active=False)
        form.instance.user = self.request.user
        response = super().form_valid(form)

        cycle = self.object
        next_period_date = cycle.start_date + timedelta(days=cycle.cycle_length)
        ovulation_date = next_period_date - timedelta(days=14)
        fertile_start = ovulation_date - timedelta(days=5)

        Reminder.objects.get_or_create(
            user=self.request.user,
            event_date=next_period_date - timedelta(days=2),
            defaults={'title': 'Kikumbusho: Hedhi yako inatarajiwa kuanza baada ya siku 2.'},
        )
        Reminder.objects.get_or_create(
            user=self.request.user,
            event_date=ovulation_date,
            defaults={'title': 'Ovulation alert: Leo ni siku ya ovulation kwa makadirio.'},
        )
        Reminder.objects.get_or_create(
            user=self.request.user,
            event_date=fertile_start,
            defaults={'title': 'Fertile window imeanza leo kwa makadirio ya AI.'},
        )

        return response

class DailyLogCreateView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, CreateView):
    model = DailyLog
    form_class = DailyLogForm
    template_name = 'menstrual/log_form.html'
    success_url = reverse_lazy('menstrual:dashboard')

    def dispatch(self, request, *args, **kwargs):
        self.active_cycle = MenstrualCycle.objects.filter(user=request.user, is_active=True).first()
        if not self.active_cycle:
            messages.warning(request, "Tafadhali anza mzunguko mpya kwanza ili uweze kuweka kumbukumbu.")
            return redirect('menstrual:dashboard')
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        initial = super().get_initial()
        selected_date = self.request.GET.get('date')
        if selected_date:
            initial['date'] = selected_date
        return initial

    def form_valid(self, form):
        # Onyo: Angalia ikiwa log kwa tarehe hii tayari ipo
        date = form.cleaned_data.get('date')
        if DailyLog.objects.filter(cycle=self.active_cycle, date=date).exists():
            form.add_error('date', "Tayari umeshaweka kumbukumbu kwa tarehe hii. Huwezi kuweka mbili kwa siku moja.")
            return self.form_invalid(form)
        form.instance.cycle = self.active_cycle
        messages.success(self.request, "Kumbukumbu imehifadhiwa kwa mafanikio!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Kuna tatizo kwenye taarifa ulizoingiza. Tafadhali angalia makosa na ujaribu tena.")
        return super().form_invalid(form)

class DailyLogUpdateView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, UpdateView):
    model = DailyLog
    form_class = DailyLogForm
    template_name = 'menstrual/log_form.html'
    success_url = reverse_lazy('menstrual:dashboard')

    def get_queryset(self):
        return DailyLog.objects.filter(cycle__user=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Kumbukumbu imerekebishwa kwa mafanikio!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Marekebisho hayajahifadhiwa. Tafadhali rekebisha makosa kwenye fomu.")
        return super().form_invalid(form)

class ForumListView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, ListView):
    def get(self, request, *args, **kwargs):
        return redirect('chats:feed')

class DoctorListView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, ListView):
    def get(self, request, *args, **kwargs):
        return redirect('doctor:hub')

class VerifyDoctorView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        # Attempts to find the profile associated with the current user
        profile = get_object_or_404(DoctorProfile, user=request.user)
        profile.verified = True
        profile.save()
        
        messages.success(request, "Wasifu wako umethibitishwa kwa mafanikio!")
        return redirect('menstrual:doctor_list')

class MarkReminderReadView(FemaleMenstrualOnlyMixin, LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
        reminder.is_notified = True
        reminder.save()
        return redirect(request.META.get('HTTP_REFERER', 'menstrual:dashboard'))