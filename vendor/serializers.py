from rest_framework import serializers
from .models import VendorProfile


class SimpleVendorProfileSerializer(serializers.ModelSerializer):
    """Lightweight vendor payload for list/summary views."""
    class Meta:
        model = VendorProfile
        fields = [
            'id', 'name', 'slug', 'logo',
            'city', 'country',
            'avg_rating', 'total_reviews',
            'is_verified', 'verification_status',
        ]


class VendorProfileSerializer(SimpleVendorProfileSerializer):
    """Backward-compatible alias for existing imports."""


class VendorDetailSerializer(serializers.ModelSerializer):
    """Full store detail page data."""
    can_resubmit = serializers.SerializerMethodField()
    has_submitted_before = serializers.SerializerMethodField()

    class Meta:
        model = VendorProfile
        fields = [
            'id', 'name', 'slug', 'description',
            'logo', 'banner_image',
            'contact_email', 'contact_phone',
            'secondary_phone', 'otp_number',
            'address', 'city', 'zone', 'area', 'country',
            'avg_rating', 'total_reviews',
            'is_verified',
            'verification_status',
            'last_submitted_at',
            'has_submitted_before',
            'can_resubmit',
            'profile_completed',
            'created_at', 'updated_at',
        ]

    def get_can_resubmit(self, obj):
        return obj.verification_status != VendorProfile.VerificationStatus.BLOCKED

    def get_has_submitted_before(self, obj):
        return obj.last_submitted_at is not None


class VendorProfileSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorProfile
        fields = [
            'name',
            'description',
            'logo',
            'banner_image',
            'contact_email',
            'contact_phone',
            'secondary_phone',
            'otp_number',
            'address',
            'city',
            'zone',
            'area',
            'country',
        ]

    def validate(self, attrs):
        city = attrs.get('city', getattr(self.instance, 'city', None))
        zone = attrs.get('zone', getattr(self.instance, 'zone', None))
        area = attrs.get('area', getattr(self.instance, 'area', None))

        if city and zone and zone.city_id != city.city_id:
            raise serializers.ValidationError({'zone': 'Selected zone does not belong to the selected city.'})
        if zone and area and area.zone_id != zone.zone_id:
            raise serializers.ValidationError({'area': 'Selected area does not belong to the selected zone.'})

        return attrs
