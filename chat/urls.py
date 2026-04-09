from django.urls import path

from .views import (
    ConversationDetailView,
    ConversationListCreateView,
    MarkConversationReadView,
    MessageCreateView,
)


urlpatterns = [
    path('conversations/', ConversationListCreateView.as_view(), name='chat-conversation-list-create'),
    path('conversations/<uuid:id>/', ConversationDetailView.as_view(), name='chat-conversation-detail'),
    path('conversations/<uuid:conversation_id>/messages/', MessageCreateView.as_view(), name='chat-message-create'),
    path('conversations/<uuid:conversation_id>/read/', MarkConversationReadView.as_view(), name='chat-conversation-read'),
]
