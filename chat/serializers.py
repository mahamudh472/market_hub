from rest_framework import serializers

from .models import Conversation, Message
from products.models import Product
from accounts.models import User


class ConversationCreateSerializer(serializers.Serializer):
    vendor_id = serializers.UUIDField()
    product_id = serializers.UUIDField(required=False)

    def validate_vendor_id(self, value):
        vendor = User.objects.filter(id=value, role='vendor', is_active=True).first()
        if not vendor:
            raise serializers.ValidationError('Vendor not found.')
        return value

    def validate_product_id(self, value):
        if not Product.objects.filter(id=value).exists():
            raise serializers.ValidationError('Product not found.')
        return value

    def validate(self, attrs):
        request = self.context['request']
        if request.user.role != 'customer':
            raise serializers.ValidationError('Only customers can start a conversation.')

        product_id = attrs.get('product_id')
        vendor_id = attrs['vendor_id']

        if product_id:
            product = Product.objects.select_related('vendor__user').filter(id=product_id).first()
            if not product:
                raise serializers.ValidationError({'product_id': 'Product not found.'})
            if str(product.vendor.user_id) != str(vendor_id):
                raise serializers.ValidationError({'vendor_id': 'Vendor does not own this product.'})

        return attrs


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.CharField(source='sender.role', read_only=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            'id',
            'conversation',
            'sender',
            'sender_name',
            'sender_role',
            'text',
            'file',
            'file_url',
            'file_name',
            'file_content_type',
            'file_size',
            'is_read',
            'read_at',
            'created_at',
        ]
        read_only_fields = [
            'id',
            'conversation',
            'sender',
            'sender_name',
            'sender_role',
            'file_url',
            'is_read',
            'read_at',
            'created_at',
        ]

    def get_sender_name(self, obj):
        return obj.sender.full_name or obj.sender.email

    def get_file_url(self, obj):
        if not obj.file:
            return None
        request = self.context.get('request')
        if request:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url

    def validate(self, attrs):
        if not attrs.get('text') and not attrs.get('file'):
            raise serializers.ValidationError('Either text or file must be provided.')
        return attrs


class ConversationListSerializer(serializers.ModelSerializer):
    participant = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    last_message_object = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'customer',
            'vendor',
            'product',
            'participant',
            'last_message',
            'last_message_at',
            'last_message_object',
            'unread_count',
            'created_at',
            'updated_at',
        ]

    def get_participant(self, obj):
        request_user = self.context['request'].user
        other_user = obj.vendor if request_user.id == obj.customer_id else obj.customer
        return {
            'id': str(other_user.id),
            'email': other_user.email,
            'full_name': other_user.full_name,
            'avatar': other_user.avatar.url if other_user.avatar else None,
            'role': other_user.role,
        }

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()

    def get_last_message_object(self, obj):
        message = obj.messages.order_by('-created_at').first()
        if not message:
            return None
        return MessageSerializer(message, context=self.context).data


class ConversationDetailSerializer(serializers.ModelSerializer):
    messages = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'customer',
            'vendor',
            'product',
            'last_message',
            'last_message_at',
            'messages',
            'unread_count',
            'created_at',
            'updated_at',
        ]

    def get_messages(self, obj):
        messages = obj.messages.select_related('sender').all()
        return MessageSerializer(messages, many=True, context=self.context).data

    def get_unread_count(self, obj):
        user = self.context['request'].user
        return obj.messages.filter(is_read=False).exclude(sender=user).count()
