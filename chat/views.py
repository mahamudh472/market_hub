from django.db.models import Q
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import Conversation, Message
from .serializers import (
	ConversationCreateSerializer,
	ConversationDetailSerializer,
	ConversationListSerializer,
	MessageSerializer,
)
from accounts.models import User


class ConversationListCreateView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		conversations = (
			Conversation.objects
			.filter(Q(customer=request.user) | Q(vendor=request.user))
			.select_related('customer', 'vendor', 'product')
			.prefetch_related('messages__sender')
			.order_by('-last_message_at', '-updated_at')
		)
		serializer = ConversationListSerializer(conversations, many=True, context={'request': request})
		return Response(serializer.data, status=status.HTTP_200_OK)

	def post(self, request):
		serializer = ConversationCreateSerializer(data=request.data, context={'request': request})
		serializer.is_valid(raise_exception=True)

		vendor = User.objects.get(id=serializer.validated_data['vendor_id'])
		product_id = serializer.validated_data.get('product_id')
		defaults = {'last_message_at': timezone.now()}

		conversation, created = Conversation.objects.get_or_create(
			customer=request.user,
			vendor=vendor,
			product_id=product_id,
			defaults=defaults,
		)
		response_serializer = ConversationDetailSerializer(conversation, context={'request': request})
		return Response(
			response_serializer.data,
			status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
		)


class ConversationDetailView(generics.RetrieveAPIView):
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = ConversationDetailSerializer
	lookup_field = 'id'

	def get_queryset(self):
		return (
			Conversation.objects
			.filter(Q(customer=self.request.user) | Q(vendor=self.request.user))
			.select_related('customer', 'vendor', 'product')
			.prefetch_related('messages__sender')
		)


class MessageCreateView(generics.GenericAPIView):
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = MessageSerializer

	def post(self, request, conversation_id):
		conversation = (
			Conversation.objects
			.filter(id=conversation_id)
			.filter(Q(customer=request.user) | Q(vendor=request.user))
			.first()
		)
		if not conversation:
			return Response({'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

		serializer = self.serializer_class(data=request.data, context={'request': request})
		serializer.is_valid(raise_exception=True)
		message = serializer.save(conversation=conversation, sender=request.user)

		if message.file:
			message.file_name = message.file_name or message.file.name.split('/')[-1]
			message.file_size = message.file_size or message.file.size
			message.save(update_fields=['file_name', 'file_size'])

		message_text = message.text or (message.file_name or 'File sent')
		conversation.last_message = message_text
		conversation.last_message_at = message.created_at
		conversation.save(update_fields=['last_message', 'last_message_at', 'updated_at'])

		payload = MessageSerializer(message, context={'request': request}).data
		channel_layer = get_channel_layer()
		async_to_sync(channel_layer.group_send)(
			f'chat_{conversation.id}',
			{
				'type': 'chat_message',
				'message': payload,
			},
		)

		return Response(payload, status=status.HTTP_201_CREATED)


class MarkConversationReadView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, conversation_id):
		conversation = (
			Conversation.objects
			.filter(id=conversation_id)
			.filter(Q(customer=request.user) | Q(vendor=request.user))
			.first()
		)
		if not conversation:
			return Response({'detail': 'Conversation not found.'}, status=status.HTTP_404_NOT_FOUND)

		updated_count = (
			Message.objects
			.filter(conversation=conversation, is_read=False)
			.exclude(sender=request.user)
			.update(is_read=True, read_at=timezone.now())
		)

		return Response({'updated': updated_count}, status=status.HTTP_200_OK)
