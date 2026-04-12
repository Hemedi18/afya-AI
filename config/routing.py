# Django Channels routing for delivery agent location updates
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path
from delivery.consumers import AgentLocationConsumer

application = ProtocolTypeRouter({
    "websocket": AuthMiddlewareStack(
        URLRouter([
            path("ws/delivery/agent/", AgentLocationConsumer.as_asgi()),
        ])
    ),
})
