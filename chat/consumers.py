import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.db.models import Q
from django.utils import timezone
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import Conversation, Message
from accounts.models import User


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user: User | None = None
        url_route = self.scope.get('url_route') or {}
        kwargs = url_route.get('kwargs', {}) if isinstance(url_route, dict) else {}
        self.conversation_id = kwargs.get('conversation_id')
        if not self.conversation_id:
            await self.close(code=4400)
            return

        self.room_group_name = f'chat_{self.conversation_id}'

        token = self._extract_token()
        if not token:
            await self.close(code=4401)
            return

        user = await self._get_user_from_token(token)
        if not user:
            await self.close(code=4401)
            return

        has_access = await self._has_conversation_access(user.id)
        if not has_access:
            await self.close(code=4403)
            return

        self.user = user

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return

        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(json.dumps({'error': 'Invalid JSON payload.'}))
            return

        message_type = payload.get('type', 'message')
        if message_type == 'message':
            await self._handle_send_message(payload)
            return

        if message_type == 'mark_read':
            if not self.user:
                await self.send(json.dumps({'error': 'Unauthorized.'}))
                return

            updated = await self._mark_messages_read()
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_read_receipt',
                    'conversation_id': str(self.conversation_id),
                    'updated': updated,
                    'reader_id': str(self.user.id),
                },
            )
            return

        await self.send(json.dumps({'error': 'Unsupported message type.'}))

    async def _handle_send_message(self, payload):
        text = payload.get('text')

        # File upload is handled through HTTP endpoint only.
        if payload.get('file_data') or payload.get('file_name') or payload.get('file_content_type'):
            await self.send(json.dumps({'error': 'Send files via HTTP endpoint, not WebSocket.'}))
            return

        if not text:
            await self.send(json.dumps({'error': 'text is required.'}))
            return

        message = await self._create_message(
            text=text,
        )

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
            },
        )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {'type': 'message', 'data': event['message']},
                default=str,
            )
        )

    async def chat_read_receipt(self, event):
        await self.send(
            text_data=json.dumps(
                {'type': 'read_receipt', 'data': event},
                default=str,
            )
        )

    def _extract_token(self):
        query_string = self.scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        token_values = params.get('token')
        if not token_values:
            return None
        return token_values[0]

    @database_sync_to_async
    def _get_user_from_token(self, raw_token):
        try:
            validator = JWTAuthentication()
            validated_token = validator.get_validated_token(raw_token)
            user = validator.get_user(validated_token)
            return user if user.is_active else None
        except (InvalidToken, TokenError, Exception):
            return None

    @database_sync_to_async
    def _has_conversation_access(self, user_id):
        return Conversation.objects.filter(
            id=self.conversation_id,
        ).filter(
            Q(customer_id=user_id) | Q(vendor_id=user_id),
        ).exists()

    @database_sync_to_async
    def _create_message(self, text):
        conversation = Conversation.objects.get(id=self.conversation_id)
        if not self.user:
            raise ValueError('User is not set on websocket connection.')

        sender = self.user

        message = Message.objects.create(conversation=conversation, sender=sender, text=text)

        conversation.last_message = message.text or message.file_name or 'File sent'
        conversation.last_message_at = message.created_at
        conversation.save(update_fields=['last_message', 'last_message_at', 'updated_at'])

        return {
            'id': str(message.id),
            'conversation': str(conversation.id),
            'sender': str(sender.id),
            'sender_name': sender.full_name or sender.email,
            'sender_role': sender.role,
            'text': message.text,
            'file_url': None,
            'file_name': None,
            'file_content_type': None,
            'file_size': None,
            'is_read': message.is_read,
            'read_at': None,
            'created_at': message.created_at.isoformat(),
        }

    @database_sync_to_async
    def _mark_messages_read(self):
        if not self.user:
            return 0

        return (
            Message.objects
            .filter(conversation_id=self.conversation_id, is_read=False)
            .exclude(sender=self.user)
            .update(is_read=True, read_at=timezone.now())
        )
