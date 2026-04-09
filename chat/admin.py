from django.contrib import admin

from .models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
	list_display = ('id', 'customer', 'vendor', 'product', 'last_message_at', 'created_at')
	search_fields = ('customer__email', 'vendor__email')
	list_filter = ('created_at', 'last_message_at')


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
	list_display = ('id', 'conversation', 'sender', 'is_read', 'created_at')
	search_fields = ('conversation__id', 'sender__email', 'text')
	list_filter = ('is_read', 'created_at')
