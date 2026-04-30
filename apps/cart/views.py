from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Cart, CartItem, Voucher, VoucherUsage
from .serializers import CartSerializer, CartItemSerializer, ApplyVoucherSerializer


def get_or_create_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


class CartDetailView(APIView):
    """GET  /cart/  — return the current user's cart with order summary."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_or_create_cart(request.user)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)


class CartItemAddView(APIView):
    """POST /cart/items/  — add a product (+ optional variant) to cart."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        cart = get_or_create_cart(request.user)
        serializer = CartItemSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        product = serializer.validated_data['product']
        variant = serializer.validated_data.get('variant')
        quantity = serializer.validated_data.get('quantity', 1)

        item, created = CartItem.objects.get_or_create(
            cart=cart, product=product, variant=variant,
            defaults={'quantity': quantity},
        )
        if not created:
            item.quantity += quantity
            item.save()

        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data, status=status.HTTP_200_OK)


class CartItemUpdateView(APIView):
    """PATCH /cart/items/<id>/  — set exact quantity."""
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        cart = get_or_create_cart(request.user)
        try:
            item = cart.items.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found in your cart.'}, status=status.HTTP_404_NOT_FOUND)

        quantity = request.data.get('quantity')
        if quantity is None:
            return Response({'error': 'quantity is required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            quantity = int(quantity)
            if quantity < 1:
                raise ValueError
        except (ValueError, TypeError):
            return Response({'error': 'quantity must be a positive integer.'}, status=status.HTTP_400_BAD_REQUEST)

        # Check stock
        stock = item.variant.stock if item.variant else item.product.stock
        if quantity > stock:
            return Response({'error': f'Only {stock} units available.'}, status=status.HTTP_400_BAD_REQUEST)

        item.quantity = quantity
        item.save()

        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)


class CartItemDeleteView(APIView):
    """DELETE /cart/items/<id>/  — remove an item from cart."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        cart = get_or_create_cart(request.user)
        try:
            item = cart.items.get(id=item_id)
        except CartItem.DoesNotExist:
            return Response({'error': 'Item not found in your cart.'}, status=status.HTTP_404_NOT_FOUND)

        item.delete()
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)


class CartClearView(APIView):
    """DELETE /cart/clear/  — remove all items."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        cart = get_or_create_cart(request.user)
        cart.items.all().delete()
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)


class ApplyVoucherView(APIView):
    """POST /cart/voucher/apply/  — attach a voucher to the cart."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ApplyVoucherSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        code = serializer.validated_data['code']
        cart = get_or_create_cart(request.user)
        now = timezone.now()

        try:
            voucher = Voucher.objects.get(code__iexact=code, is_active=True)
        except Voucher.DoesNotExist:
            return Response({'error': 'Invalid or expired voucher code.'}, status=status.HTTP_400_BAD_REQUEST)

        # Time validity
        if not (voucher.valid_from <= now <= voucher.valid_until):
            return Response({'error': 'This voucher is not currently valid.'}, status=status.HTTP_400_BAD_REQUEST)

        # Global usage limit
        if voucher.usage_limit and voucher.used_count >= voucher.usage_limit:
            return Response({'error': 'Voucher usage limit reached.'}, status=status.HTTP_400_BAD_REQUEST)

        # Per-user limit
        user_usage = VoucherUsage.objects.filter(voucher=voucher, user=request.user).count()
        if user_usage >= voucher.per_user_limit:
            return Response({'error': 'You have already used this voucher.'}, status=status.HTTP_400_BAD_REQUEST)

        subtotal = cart.get_subtotal()
        if subtotal < voucher.min_order_amount:
            return Response(
                {'error': f'Minimum order amount of {voucher.min_order_amount} required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart.voucher = voucher
        cart.save()

        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response({
            'message': 'Voucher applied successfully.',
            'cart': cart_serializer.data,
        })


class RemoveVoucherView(APIView):
    """DELETE /cart/voucher/remove/  — detach the voucher from cart."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        cart = get_or_create_cart(request.user)
        cart.voucher = None
        cart.save()
        cart_serializer = CartSerializer(cart, context={'request': request})
        return Response(cart_serializer.data)
