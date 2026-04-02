from django.urls import path

from .views import (
    MobileConversationDetailApiView,
    MobileConversationListApiView,
    MobileLoginApiView,
    MobileRegisterApiView,
    MobileLogoutApiView,
    MobileMeApiView,
    MobileStartConversationApiView,
)


urlpatterns = [
    path('auth/login/', MobileLoginApiView.as_view(), name='mobile_login'),
    path('auth/register/', MobileRegisterApiView.as_view(), name='mobile_register'),
    path('auth/logout/', MobileLogoutApiView.as_view(), name='mobile_logout'),
    path('auth/me/', MobileMeApiView.as_view(), name='mobile_me'),
    path('chats/', MobileConversationListApiView.as_view(), name='mobile_chats'),
    path('chats/start/', MobileStartConversationApiView.as_view(), name='mobile_chats_start'),
    path('chats/<int:conversation_id>/', MobileConversationDetailApiView.as_view(), name='mobile_chat_detail'),
]
