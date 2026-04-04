from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
from django.http import Http404
from django.views.static import serve as static_serve
from offline_chat.views import sms_webhook, android_sms_webhook, twilio_sms_webhook
from main.views import pwa_manifest, service_worker, runtime_translation_map


def local_media_serve(request, path):
    host = (request.get_host() or '').split(':')[0]
    if settings.DEBUG or host in {'127.0.0.1', 'localhost'}:
        return static_serve(request, path, document_root=settings.MEDIA_ROOT)
    raise Http404()

urlpatterns = [
    # URLs ambazo hazihitaji lugha ziwe hapa (kama API)
    path('i18n/', include('django.conf.urls.i18n')),
    path('i18n/runtime-map.json', runtime_translation_map, name='runtime_translation_map'),
    path('accounts/', include('allauth.urls')),
    path('api/mobile/', include('mobile_api.urls')),
    path('api/medics/', include('medics.api_urls')),
    path('api/diseases/', include('diseases.api_urls')),
    path('manifest.webmanifest', pwa_manifest, name='pwa_manifest'),
    path('service-worker.js', service_worker, name='pwa_service_worker'),
    # SMS webhook routes (no i18n prefix, no redirect)
    path('sms/webhook/', sms_webhook, name='sms_webhook_public'),
    path('sms/webhook', sms_webhook),
    path('offline/sms/webhook/', sms_webhook),
    path('offline/sms/webhook', sms_webhook),
    path('sms/twilio/webhook/', twilio_sms_webhook, name='twilio_sms_webhook_public'),
    path('sms/twilio/webhook', twilio_sms_webhook),
    path('sms/android/webhook/', android_sms_webhook, name='android_sms_webhook_public'),
    path('sms/android/webhook', android_sms_webhook),
    path('media/<path:path>', local_media_serve, name='local_media_serve'),
]

# URLs zinazobadilika lugha
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('menstrual/', include('menstrual.urls')),
    path('reproduction/', include('reproduction.urls')),
    path('social/', include('chats.urls')),
    path('doctor/', include('doctor.urls')),
    path('card/', include('card.urls')),
    path('medics/', include('medics.urls')),
    path('diseases/', include('diseases.urls')),
    path('ai/', include('AI_brain.urls')),
    path('ml/', include('machine_learning.urls')),
    path('offline/', include('offline_chat.urls')),
    path('users/', include('users.urls')),
)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)