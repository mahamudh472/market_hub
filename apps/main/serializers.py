from rest_framework import serializers
from .models import HomeBanner, Wishlist
from apps.products.serializers import SimpleProductSerializer


class HomeBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeBanner
        fields = ['id', 'title', 'image', 'destination_url', 'sort_order', 'created_at']


class WishlistSerializer(serializers.ModelSerializer):
    product = SimpleProductSerializer(read_only=True)

    class Meta:
        model = Wishlist
        fields = ['id', 'product', 'added_at']

