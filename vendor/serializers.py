from rest_framework import serializers
from .models import VendorProfile


class VendorProfileSerializer(serializers.ModelSerializer):
    """Compact vendor card used in product listings."""
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'name', 'slug', 'logo',
            'city', 'country',
            'avg_rating', 'total_reviews',
            'is_verified',
        ]


class VendorDetailSerializer(serializers.ModelSerializer):
    """Full store detail page data."""
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'name', 'slug', 'description',
            'logo', 'banner_image',
            'contact_email', 'contact_phone',
            'address', 'city', 'country',
            'avg_rating', 'total_reviews',
            'is_verified', 'created_at',
        ]
