from rest_framework import serializers
from .models import HomeBanner
from products.serializers import CategorySerializer

class HomeBannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeBanner
        fields = ['id', 'title', 'image', 'destination_url', 'created_at']



class HomeDataSerializer(serializers.Serializer):
    banners = serializers.SerializerMethodField()
