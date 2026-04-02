from django.urls import path

from .views import AIChatView, AIQuickChatView, AIFeedbackView

app_name = 'AI_brain'

urlpatterns = [
    path('chat/', AIChatView.as_view(), name='chat'),
    path('chat/quick/', AIQuickChatView.as_view(), name='chat_quick'),
    path('chat/feedback/', AIFeedbackView.as_view(), name='chat_feedback'),
]
