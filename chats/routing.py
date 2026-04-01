from django.urls import re_path

from .consumers import PrivateChatConsumer

websocket_urlpatterns = [
    re_path(r'^ws/chats/private/(?P<conversation_id>\d+)/$', PrivateChatConsumer.as_asgi()),
]
