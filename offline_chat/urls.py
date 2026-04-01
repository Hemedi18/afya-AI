from django.urls import path

from .views import OfflineChatPageView, OfflineChatSendView, OfflineConversationCreateView, sms_webhook, android_sms_webhook, twilio_sms_webhook

app_name = 'offline_chat'

urlpatterns = [
    path('', OfflineChatPageView.as_view(), name='home'),
    path('sms/webhook/', sms_webhook, name='sms_webhook'),
    path('sms/twilio/webhook/', twilio_sms_webhook, name='twilio_sms_webhook'),
    path('sms/android/webhook/', android_sms_webhook, name='android_sms_webhook'),
    path('api/send/', OfflineChatSendView.as_view(), name='send'),
    path('api/new/', OfflineConversationCreateView.as_view(), name='new_conversation'),
]
