import uuid

from django.db import models
from django.db.models import Q


class Conversation(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	customer = models.ForeignKey(
		'accounts.User',
		on_delete=models.CASCADE,
		related_name='customer_conversations',
	)
	vendor = models.ForeignKey(
		'accounts.User',
		on_delete=models.CASCADE,
		related_name='vendor_conversations',
	)
	product = models.ForeignKey(
		'products.Product',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='conversations',
	)
	last_message = models.TextField(blank=True, null=True)
	last_message_at = models.DateTimeField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = 'chat_conversations'
		ordering = ['-last_message_at', '-updated_at']
		constraints = [
			models.UniqueConstraint(
				fields=['customer', 'vendor', 'product'],
				name='uniq_customer_vendor_product_conversation',
			),
			models.UniqueConstraint(
				fields=['customer', 'vendor'],
				condition=Q(product__isnull=True),
				name='uniq_customer_vendor_without_product_conversation',
			),
		]

	def __str__(self):
		product_suffix = f' ({self.product.pk})' if self.product else ''
		return f'{self.customer.email} -> {self.vendor.email}{product_suffix}'


class Message(models.Model):
	id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
	conversation = models.ForeignKey(
		Conversation,
		on_delete=models.CASCADE,
		related_name='messages',
	)
	sender = models.ForeignKey(
		'accounts.User',
		on_delete=models.CASCADE,
		related_name='sent_messages',
	)
	text = models.TextField(blank=True, null=True)
	file = models.FileField(upload_to='chat_files/', blank=True, null=True)
	file_name = models.CharField(max_length=255, blank=True, null=True)
	file_content_type = models.CharField(max_length=120, blank=True, null=True)
	file_size = models.PositiveIntegerField(blank=True, null=True)
	is_read = models.BooleanField(default=False)
	read_at = models.DateTimeField(blank=True, null=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = 'chat_messages'
		ordering = ['created_at']

	def __str__(self):
		return f'Message({self.id}) in {self.conversation.pk}'
