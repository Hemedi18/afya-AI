from django.contrib.auth.models import User
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.templatetags.static import static
from django.views.generic import TemplateView

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['stats'] = {
            'users': User.objects.count(),
            'doctors_total': DoctorProfile.objects.count(),
            'doctors_verified': DoctorProfile.objects.filter(verified=True).count(),
            'daily_logs': DailyLog.objects.count(),
            'community_posts': CommunityPost.objects.count(),
            'pending_reminders': Reminder.objects.filter(is_notified=False).count(),
        }
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