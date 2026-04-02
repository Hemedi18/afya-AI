from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.templatetags.static import static
from django.utils import timezone
from django.views.generic import TemplateView
import json

from AI_brain.models import AIInteractionLog
from AI_brain.services import generate_ai_text
from menstrual.models import CommunityPost, DailyLog, DoctorProfile, Reminder
from users.permissions import AdminRequiredMixin
from users.utils import get_user_gender

# Create your views here.

def home(request):
    gender = get_user_gender(request.user) if request.user.is_authenticated else None
    if gender == 'female':
        welcome_tag = 'Karibu dada! Safari yako ya afya ya mzunguko inaanza hapa.'
        primary_url = 'menstrual:dashboard'
        primary_label = 'Fungua Dashboard ya Mzunguko'
    elif gender == 'male':
        welcome_tag = 'Karibu kaka! Pata mwongozo wa afya na ustawi wako hapa.'
        primary_url = 'main:male_dashboard'
        primary_label = 'Fungua Male Dashboard'
    else:
        welcome_tag = 'Karibu ZanzHub AI — Jisajili ili upate huduma zilizobinafsishwa.'
        primary_url = 'users:register'
        primary_label = 'Anza Kujisajili'

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
    return render(request, 'main/documentation.html')


def services(request):
    gender = get_user_gender(request.user) if request.user.is_authenticated else None

    common_services = [
        {
            'title': 'Medication & Drugs',
            'description': 'Mwongozo wa dawa, matumizi salama, na maelezo ya muhimu ya matibabu.',
            'image': 'https://images.unsplash.com/photo-1587854692152-cbe660dbde88?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-capsule-pill',
            'audience': 'Wote',
            'is_live': False,
            'url': None,
        },
        {
            'title': 'Diseases',
            'description': 'Elimu ya magonjwa, dalili, prevention, na hatua za awali za kujitunza.',
            'image': 'https://images.unsplash.com/photo-1579165466741-7f35e4755660?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-virus2',
            'audience': 'Wote',
            'is_live': False,
            'url': None,
        },
        {
            'title': 'Puberty & Reproduction',
            'description': 'Maelezo ya mabadiliko ya balehe na afya ya uzazi kwa lugha rahisi.',
            'image': 'https://images.unsplash.com/photo-1491438590914-bc09fcaaf77a?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-person-hearts',
            'audience': 'Wote',
            'is_live': False,
            'url': None,
        },
        {
            'title': 'Child Growth',
            'description': 'Ufuatiliaji wa ukuaji wa mtoto, milestones, na vidokezo vya malezi.',
            'image': 'https://images.unsplash.com/photo-1516627145497-ae6968895b74?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-balloon-heart',
            'audience': 'Wote',
            'is_live': False,
            'url': None,
        },
    ]

    female_services = [
        {
            'title': 'Menstrual',
            'description': 'Track mzunguko wako, dalili, na reminders kwa usahihi zaidi.',
            'image': 'https://images.unsplash.com/photo-1511174511562-5f7f18b874f8?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-calendar-heart',
            'audience': 'Wanawake',
            'is_live': True,
            'url': 'menstrual:dashboard',
        },
        {
            'title': 'Pregnancy',
            'description': 'Huduma za ujauzito, ufuatiliaji wa hatua kwa hatua, na ushauri salama.',
            'image': 'https://images.unsplash.com/photo-1544776193-352d25ca82cd?auto=format&fit=crop&w=1200&q=80',
            'icon': 'bi-heart-pulse',
            'audience': 'Wanawake',
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
        data = {
                'name': 'afya-AI Health Assistant',
                'short_name': 'afya-AI',
                'description': 'Smart private reproductive and health care assistant.',
        'id': '/',
        'start_url': '/',
                'scope': '/',
                'display': 'standalone',
                'background_color': '#F6F1FB',
                'theme_color': '#2F6B3F',
                'orientation': 'portrait',
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
                        }
                ],
        }
        return JsonResponse(data)


def service_worker(request):
        js = """
const CACHE_NAME = 'afya-ai-v2';
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
        return HttpResponse(js, content_type='application/javascript')