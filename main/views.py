from django.contrib.auth.models import User
from django.conf import settings
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.templatetags.static import static
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import TemplateView
import json
from functools import lru_cache
from pathlib import Path

from AI_brain.models import AIInteractionLog
from AI_brain.services import generate_ai_text
from menstrual.models import CommunityPost, DailyLog, DoctorProfile, Reminder
from users.permissions import AdminRequiredMixin
from users.utils import get_user_gender


@lru_cache(maxsize=1)
def _load_unified_translations():
    file_path = Path(settings.BASE_DIR) / 'locale' / 'unified_translations.json'
    try:
        with file_path.open('r', encoding='utf-8') as fh:
            payload = json.load(fh)
            return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def runtime_translation_map(request):
    lang = (request.GET.get('lang') or getattr(request, 'LANGUAGE_CODE', 'sw') or 'sw').split('-')[0]
    if lang not in {'en', 'ar'}:
        return JsonResponse({'lang': lang, 'map': {}})

    mapping = {}
    source = _load_unified_translations()
    for _, row in source.items():
        if not isinstance(row, dict):
            continue
        sw_text = (row.get('sw') or '').strip()
        target_text = (row.get(lang) or '').strip()
        if sw_text and target_text and sw_text != target_text:
            mapping[sw_text] = target_text

    return JsonResponse({'lang': lang, 'map': mapping})

# Create your views here.

def home(request):
    gender = get_user_gender(request.user) if request.user.is_authenticated else None
    if gender == 'female':
        welcome_tag = _('Karibu dada! Safari yako ya afya ya mzunguko inaanza hapa.')
        primary_url = 'menstrual:dashboard'
        primary_label = _('Fungua Dashboard ya Mzunguko')
    elif gender == 'male':
        welcome_tag = _('Karibu kaka! Pata mwongozo wa afya na ustawi wako hapa.')
        primary_url = 'main:male_dashboard'
        primary_label = _('Fungua Male Dashboard')
    else:
        welcome_tag = _('Karibu AfyaSmart — Jisajili ili upate huduma zilizobinafsishwa.')
        primary_url = 'users:register'
        primary_label = _('Anza Kujisajili')

    return render(
        request,
        'main/home.html',
        {
            'welcome_tag': welcome_tag,
            'primary_url': primary_url,
            'primary_label': primary_label,
            'user_gender': gender,
        },
    )


def male_dashboard(request):
    if request.user.is_authenticated and get_user_gender(request.user) == 'female':
        return redirect('menstrual:dashboard')
    return render(request, 'main/male_dashboard.html')

def about(request):
    return render(request, 'main/about.html')

def contact(request):
    return render(request, 'main/contact.html')

def documentation(request):
    gender = get_user_gender(request.user) if request.user.is_authenticated else None

    if request.user.is_authenticated:
        starter_title = _('Your personalized getting-started guide')
        starter_intro = _('These first steps are prepared based on your account status, selected profile context, and the services most relevant to you now.')
    else:
        starter_title = _('Start here as a new user')
        starter_intro = _('If you are not logged in yet, follow these steps to unlock the right services, keep your data safe, and get better insights from the platform.')

    starter_steps = [
        {
            'title': _('Create an account or sign in'),
            'copy': _('Register first or sign in so the system can remember your data, language preferences, and usage history.'),
            'url': 'users:register' if not request.user.is_authenticated else 'users:profile',
            'button': _('Open registration') if not request.user.is_authenticated else _('Open profile'),
            'icon': 'bi-person-plus',
        },
        {
            'title': _('Complete core profile info'),
            'copy': _('Set gender, birth date, and key health context so AI and dashboards can provide guidance that matches you better.'),
            'url': 'users:settings',
            'button': _('Account settings'),
            'icon': 'bi-sliders',
        },
        {
            'title': _('Start with main services'),
            'copy': _('After core setup, open AI Chat, the medication library, the disease library, or the dashboard that matches your needs.'),
            'url': 'main:services',
            'button': _('Open services'),
            'icon': 'bi-grid-1x2-fill',
        },
    ]

    if gender == 'female':
        starter_steps.append(
            {
                'title': _('Open cycle dashboard'),
                'copy': _('For female users, the cycle dashboard is the main place for cycle setup, daily logs, reminders, reports, and personal trends.'),
                'url': 'menstrual:dashboard',
                'button': _('Cycle dashboard'),
                'icon': 'bi-calendar-heart',
            }
        )
    else:
        starter_steps.append(
            {
                'title': _('Open daily wellness dashboard'),
                'copy': _('For male users or users not using cycle tracking, this dashboard provides daily wellness guidance, AI support, and quick access to other services.'),
                'url': 'main:male_dashboard',
                'button': _('Open dashboard'),
                'icon': 'bi-activity',
            }
        )

    feature_guides = [
        {
            'title': _('AI Chat (text and voice)'),
            'icon': 'bi-robot',
            'url': 'AI_brain:chat',
            'button': _('Open AI Chat'),
            'summary': _('Ask health questions by text or voice. The assistant may ask follow-up questions before a final response to improve accuracy.'),
            'details': [
                _('Type a direct question or use the voice button to record a voice note.'),
                _('Voice notes are transcribed first, then answered in standard chat format.'),
                _('Symptom-related questions may trigger clarification options before final guidance.'),
                _('AI is not a doctor; urgent danger signs should always be treated as emergency care cases.'),
            ],
        },
        {
            'title': _('Medication library'),
            'icon': 'bi-capsule-pill',
            'url': 'medics:browse',
            'button': _('Open medications'),
            'summary': _('Browse medication information including use cases, ingredients, mechanism, common side effects, FAQs, and doctor guidance.'),
            'details': [
                _('Use search by brand or generic name.'),
                _('Open detail pages for dosage, manufacturer, side effects, and trusted references.'),
                _('This content is educational and should not replace professional prescription advice.'),
            ],
        },
        {
            'title': _('Disease library'),
            'icon': 'bi-virus2',
            'url': 'diseases:browse',
            'button': _('Open diseases'),
            'summary': _('View disease definitions, symptoms, prevention, basic treatment, potential complications, and first self-care guidance.'),
            'details': [
                _('Search by disease name or ICD code.'),
                _('Review symptoms, prevention, treatment basics, and risk warnings.'),
                _('Use this information for awareness, not as a substitute for diagnosis.'),
            ],
        },
        {
            'title': _('Community and social feed'),
            'icon': 'bi-people-fill',
            'url': 'chats:feed',
            'button': _('Open community'),
            'summary': _('Use posts, 24-hour status, groups, comments, and private chats in a supportive community flow.'),
            'details': [
                _('You can post, comment, like, share status, and request clarifications from doctors/admins.'),
                _('Community audience filters help keep content relevant to each user context.'),
                _('Use report tools if you find unsafe or inappropriate content.'),
            ],
        },
        {
            'title': _('Doctors and expert guidance'),
            'icon': 'bi-heart-pulse',
            'url': 'doctor:hub',
            'button': _('Open doctors hub'),
            'summary': _('When you need professional help, review verified doctors, profiles, ratings, and available support channels.'),
            'details': [
                _('Doctor hub highlights verified professionals and their specialties.'),
                _('You can request clarifications through role-based workflows.'),
                _('Assigned patients can submit requested logs from the patient log area.'),
            ],
        },
        {
            'title': _('Health card and shareable profile'),
            'icon': 'bi-person-vcard',
            'url': 'card:home',
            'button': _('Open health card'),
            'summary': _('Organize key health data in a single profile that can be shared securely according to your visibility settings.'),
            'details': [
                _('You can set profile photo, health notes, medications, goals, and visibility options.'),
                _('Public card access can be password-protected.'),
            ],
        },
    ]

    if gender == 'female':
        feature_guides.insert(
            1,
            {
                'title': _('Cycle dashboard and daily logs'),
                'icon': 'bi-calendar2-heart',
                'url': 'menstrual:dashboard',
                'button': _('Open dashboard'),
                'summary': _('Your central cycle-care area for setup, daily logs, reports, reminders, women community access, and cycle-related medical support.'),
                'details': [
                    _('Start by setting cycle start date, cycle length, and period duration.'),
                    _('Log flow intensity, physical symptoms, emotional changes, and sleep patterns.'),
                    _('Track predictions and trends from your recent entries.'),
                    _('Consistent logging improves report quality significantly.'),
                ],
            },
        )
    else:
        feature_guides.insert(
            1,
            {
                'title': _('Male wellness / daily health dashboard'),
                'icon': 'bi-speedometer2',
                'url': 'main:male_dashboard',
                'button': _('Open dashboard'),
                'summary': _('A daily wellness landing area for male users or users not using cycle tracking.'),
                'details': [
                    _('Use it as a quick start point before AI chat, disease library, or doctor services.'),
                    _('It supports lifestyle, exercise, sleep, nutrition, and daily health awareness guidance.'),
                ],
            },
        )

    privacy_points = [
        _('Your health data is used to improve responses only when relevant to your request.'),
        _('You can control privacy settings from account settings and dashboard-level options.'),
        _('Community participation can be anonymous depending on your preferences.'),
        _('AI guidance does not replace professional diagnosis, especially for emergency signs.'),
    ]

    troubleshooting = [
        {
            'title': _('Cannot sign in or register'),
            'copy': _('Check your email, username, and password. If the issue continues, use contact support or an available social login provider.'),
        },
        {
            'title': _('AI Chat response is not accurate enough'),
            'copy': _('Ask a direct question and include key symptoms, duration, and important context. Use feedback buttons after each response.'),
        },
        {
            'title': _('Voice message is not transcribed well'),
            'copy': _('Record in a quiet place, speak clearly near the microphone, and try again. Use text as backup if needed.'),
        },
        {
            'title': _('Predictions or reports look weak'),
            'copy': _('Make sure cycle setup is complete and daily logs are entered consistently. Limited data reduces trend quality.'),
        },
        {
            'title': _('Community media is not loading'),
            'copy': _('Fallback images are enabled for missing media. Refresh the page and contact support if the issue persists.'),
        },
    ]

    faq_items = [
        {
            'q': _('Do I need to fill every profile field?'),
            'a': _('Not immediately. However, richer profile data improves insight quality and personalization.'),
        },
        {
            'q': _('Can AI give me a final diagnosis?'),
            'a': _('No. AI gives education and early guidance. Final diagnosis requires professional assessment and sometimes tests.'),
        },
        {
            'q': _('When should I use voice chat instead of text?'),
            'a': _('Use voice when typing is difficult or slower. Use text for precise details like medication names and numbers.'),
        },
        {
            'q': _('Why is daily logging important?'),
            'a': _('Consistent logs create stronger patterns. Without enough data, reports, predictions, and contextual AI responses become weaker.'),
        },
    ]

    return render(
        request,
        'main/documentation.html',
        {
            'user_gender': gender,
            'starter_title': starter_title,
            'starter_intro': starter_intro,
            'starter_steps': starter_steps,
            'feature_guides': feature_guides,
            'privacy_points': privacy_points,
            'troubleshooting_items': troubleshooting,
            'faq_items': faq_items,
        },
    )


def services(request):
    gender = get_user_gender(request.user) if request.user.is_authenticated else None

    common_services = [
        {
            'title': _('Drugs & Usage'),
            'description': _('Medication library with visual cards, safe-use guidance, and key treatment details.'),
            'image': 'https://images.unsplash.com/photo-1587854692152-cbe660dbde88?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-capsule-pill',
            'audience': _('Everyone'),
            'is_live': True,
            'url': 'medics:browse',
        },
        {
            'title': _('Diseases'),
            'description': _('Disease education with visual cards, symptoms, prevention, and first self-care steps.'),
            'image': 'https://images.unsplash.com/photo-1579165466741-7f35e4755660?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-virus2',
            'audience': _('Everyone'),
            'is_live': True,
            'url': 'diseases:browse',
        },
        {
            'title': _('Puberty & Reproductive Health'),
            'description': _('Clear guidance about puberty changes and reproductive health.'),
            'image': 'https://images.unsplash.com/photo-1491438590914-bc09fcaaf77a?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-person-hearts',
            'audience': _('Everyone'),
            'is_live': False,
            'url': None,
        },
        {
            'title': _('Child Growth'),
            'description': _('Track child growth, milestones, and practical parenting tips.'),
            'image': 'https://images.unsplash.com/photo-1516627145497-ae6968895b74?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-balloon-heart',
            'audience': _('Everyone'),
            'is_live': False,
            'url': None,
        },
    ]

    female_services = [
        {
            'title': _('Menstrual Cycle Tracker'),
            'description': _('Track your cycle, symptoms, and reminders with better accuracy.'),
            'image': 'https://images.unsplash.com/photo-1511174511562-5f7f18b874f8?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-calendar-heart',
            'audience': _('Women'),
            'is_live': True,
            'url': 'menstrual:dashboard',
        },
        {
            'title': _('Pregnancy Care'),
            'description': _('Pregnancy support, stage-by-stage tracking, and safer guidance.'),
            'image': 'https://images.unsplash.com/photo-1544776193-352d25ca82cd?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-heart-pulse',
            'audience': _('Women'),
            'is_live': False,
            'url': None,
        },
    ]

    cards = common_services + (female_services if gender == 'female' else [])

    return render(
        request,
        'main/services.html',
        {
            'service_cards': cards,
            'service_count': len(cards),
            'user_gender': gender,
        },
    )


class AdminControlCenterView(AdminRequiredMixin, TemplateView):
    template_name = 'main/admin_control_center.html'

    @staticmethod
    def _series_by_day(queryset, date_field, days=14):
        today = timezone.now().date()
        start = today - timezone.timedelta(days=days - 1)
        rows = (
            queryset.filter(**{f'{date_field}__date__gte': start})
            .annotate(day=TruncDate(date_field))
            .values('day')
            .annotate(total=Count('id'))
            .order_by('day')
        )
        mapped = {row['day']: row['total'] for row in rows}
        labels, values = [], []
        for i in range(days):
            d = start + timezone.timedelta(days=i)
            labels.append(d.strftime('%d %b'))
            values.append(int(mapped.get(d, 0)))
        return labels, values

    @staticmethod
    def _summarize_series(title, labels, values):
        if not values:
            return f"{title}: hakuna data ya kutosha kwa sasa."
        total = sum(values)
        peak = max(values)
        peak_idx = values.index(peak)
        latest = values[-1]
        avg = round(total / len(values), 2) if values else 0
        return (
            f"{title}: Jumla {total}, wastani {avg}/siku, kilele {peak} tarehe {labels[peak_idx]},"
            f" leo/ya mwisho {latest}."
        )

    @staticmethod
    def _safe_feedback_rating(log):
        payload = log.context_payload or {}
        feedback = payload.get('feedback') or {}
        if isinstance(feedback, dict):
            return (feedback.get('rating') or '').strip().lower()
        return ''

    def _build_ai_dashboard_summary(self, context):
        fallback = (
            "Muhtasari wa AI haujapatikana sasa. Tafadhali tumia takwimu na grafu zilizo juu"
            " kufanya maamuzi ya admin."
        )
        prompt = (
            "You are an analytics assistant for a health platform admin dashboard. "
            "Summarize trends in clear Swahili with practical actions. Keep it short and professional.\n\n"
            f"Stats: {context['stats']}\n"
            f"Registration series: {context['reg_values']}\n"
            f"Post series: {context['post_values']}\n"
            f"AI chat series: {context['ai_values']}\n"
            f"Content types: {context['content_type_counts']}\n"
            f"Feedback: {context['feedback_counts']}\n"
            "Return 4 bullets: growth, engagement, content, AI quality."
        )
        return generate_ai_text(prompt, fallback)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        now = timezone.now()
        thirty_days_ago = now - timezone.timedelta(days=30)

        registrations_qs = User.objects.filter(date_joined__gte=thirty_days_ago)
        posts_qs = CommunityPost.objects.filter(created_at__gte=thirty_days_ago)
        ai_chat_qs = AIInteractionLog.objects.filter(created_at__gte=thirty_days_ago).exclude(question='[USER_FEEDBACK]')
        feedback_qs = AIInteractionLog.objects.filter(created_at__gte=thirty_days_ago, question='[USER_FEEDBACK]')

        reg_labels, reg_values = self._series_by_day(User.objects.all(), 'date_joined', days=14)
        post_labels, post_values = self._series_by_day(CommunityPost.objects.all(), 'created_at', days=14)
        ai_labels, ai_values = self._series_by_day(AIInteractionLog.objects.exclude(question='[USER_FEEDBACK]'), 'created_at', days=14)

        text_only_posts = posts_qs.filter(Q(image__isnull=True) | Q(image=''), Q(video__isnull=True) | Q(video='')).count()
        image_posts = posts_qs.filter(Q(image__isnull=False) & ~Q(image='')).count()
        video_posts = posts_qs.filter(Q(video__isnull=False) & ~Q(video='')).count()

        female_audience = posts_qs.filter(audience_gender=CommunityPost.AUDIENCE_FEMALE).count()
        male_audience = posts_qs.filter(audience_gender=CommunityPost.AUDIENCE_MALE).count()
        anonymous_posts = posts_qs.filter(is_anonymous=True).count()

        feedback_up = 0
        feedback_down = 0
        for fb in feedback_qs:
            rating = self._safe_feedback_rating(fb)
            if rating == 'up':
                feedback_up += 1
            elif rating == 'down':
                feedback_down += 1

        feedback_total = feedback_up + feedback_down
        helpful_rate = round((feedback_up / feedback_total) * 100, 1) if feedback_total else 0

        prev_start = now - timezone.timedelta(days=60)
        prev_end = thirty_days_ago
        previous_registrations = User.objects.filter(date_joined__gte=prev_start, date_joined__lt=prev_end).count()
        current_registrations = registrations_qs.count()
        if previous_registrations == 0:
            registration_growth_pct = 100.0 if current_registrations > 0 else 0.0
        else:
            registration_growth_pct = round(((current_registrations - previous_registrations) / previous_registrations) * 100, 1)

        context['stats'] = {
            'users': User.objects.count(),
            'doctors_total': DoctorProfile.objects.count(),
            'doctors_verified': DoctorProfile.objects.filter(verified=True).count(),
            'daily_logs': DailyLog.objects.count(),
            'community_posts': CommunityPost.objects.count(),
            'pending_reminders': Reminder.objects.filter(is_notified=False).count(),
            'new_users_30d': current_registrations,
            'registration_growth_pct': registration_growth_pct,
            'posts_30d': posts_qs.count(),
            'ai_chats_30d': ai_chat_qs.count(),
            'helpful_rate': helpful_rate,
        }

        context['reg_labels'] = json.dumps(reg_labels)
        context['reg_values'] = reg_values
        context['post_labels'] = json.dumps(post_labels)
        context['post_values'] = post_values
        context['ai_labels'] = json.dumps(ai_labels)
        context['ai_values'] = ai_values

        context['content_type_labels'] = json.dumps(['Text Only', 'Image', 'Video'])
        context['content_type_counts'] = [text_only_posts, image_posts, video_posts]

        context['audience_labels'] = json.dumps(['Female audience', 'Male audience', 'Anonymous posts'])
        context['audience_counts'] = [female_audience, male_audience, anonymous_posts]

        context['feedback_labels'] = json.dumps(['Helpful', 'Not Helpful'])
        context['feedback_counts'] = [feedback_up, feedback_down]

        context['summary_reg'] = self._summarize_series('Usajili (siku 14)', reg_labels, reg_values)
        context['summary_posts'] = self._summarize_series('Posti (siku 14)', post_labels, post_values)
        context['summary_ai'] = self._summarize_series('AI chats (siku 14)', ai_labels, ai_values)
        context['summary_content'] = (
            f"Content type ndani ya siku 30: Text {text_only_posts}, Image {image_posts}, Video {video_posts}."
        )
        context['summary_feedback'] = (
            f"Feedback ya AI: Helpful {feedback_up}, Not helpful {feedback_down}, Helpful rate {helpful_rate}%."
        )
        context['ai_dashboard_summary'] = self._build_ai_dashboard_summary(context)

        context['latest_posts'] = CommunityPost.objects.select_related('user').order_by('-created_at')[:5]
        context['latest_doctors'] = DoctorProfile.objects.select_related('user').order_by('-id')[:5]
        return context


def pwa_manifest(request):
    start_url = '/'
    current_language = getattr(request, 'LANGUAGE_CODE', '') or 'sw'
    supported_languages = {'sw', 'en', 'ar'}
    if current_language in supported_languages:
        start_url = f'/{current_language}/'

    data = {
        'name': 'AfyaSmart Health Assistant',
        'short_name': 'AfyaSmart',
        'description': 'Smart private reproductive and health care assistant.',
        'id': '/',
        'start_url': start_url,
        'scope': '/',
        'display': 'standalone',
        'display_override': ['window-controls-overlay', 'standalone', 'minimal-ui'],
        'background_color': '#F6F1FB',
        'theme_color': '#2F6B3F',
        'lang': current_language,
        'orientation': 'portrait',
        'prefer_related_applications': False,
        'icons': [
            {
                'src': static('icons/Icon-192.png'),
                'sizes': '192x192',
                'type': 'image/png',
                'purpose': 'any',
            },
            {
                'src': static('icons/Icon-512.png'),
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'any',
            },
            {
                'src': static('icons/Icon-maskable-192.png'),
                'sizes': '192x192',
                'type': 'image/png',
                'purpose': 'maskable',
            },
            {
                'src': static('icons/Icon-maskable-512.png'),
                'sizes': '512x512',
                'type': 'image/png',
                'purpose': 'maskable',
            },
        ],
    }
    return JsonResponse(data)


def service_worker(request):
    js = """
const CACHE_NAME = 'afyasmart-v4';
const URLS = ['/static/base.css'];

function isStaticAsset(requestUrl) {
    const path = new URL(requestUrl).pathname;
    return (
        path.startsWith('/static/') ||
        path.endsWith('.css') ||
        path.endsWith('.js') ||
        path.endsWith('.png') ||
        path.endsWith('.jpg') ||
        path.endsWith('.jpeg') ||
        path.endsWith('.svg') ||
        path.endsWith('.webp') ||
        path.endsWith('.ico') ||
        path.endsWith('.woff') ||
        path.endsWith('.woff2')
    );
}

self.addEventListener('install', (event) => {
    event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(URLS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)))).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (event) => {
    if (event.request.method !== 'GET') return;

    // Never cache HTML navigations/forms to avoid stale CSRF tokens.
    if (event.request.mode === 'navigate') {
        event.respondWith(fetch(event.request).catch(() => caches.match('/')));
        return;
    }

    // Cache only static assets.
    if (!isStaticAsset(event.request.url)) {
        event.respondWith(fetch(event.request));
        return;
    }

    event.respondWith(
        caches.match(event.request).then((cached) => {
            if (cached) return cached;
            return fetch(event.request)
                .then((response) => {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
                    return response;
                })
                .catch(() => caches.match(event.request));
        })
    );
});
""".strip()
    response = HttpResponse(js, content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    return response