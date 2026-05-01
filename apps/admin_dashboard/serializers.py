from rest_framework import serializers
from apps.accounts.models import User, CustomerProfile
from apps.vendor.models import VendorProfile
from apps.products.models import Category

class AdminCustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name')
    email = serializers.EmailField(source='user.email', read_only=True)
    joined_date = serializers.DateTimeField(source='user.joined_at', read_only=True)
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    total_spent = serializers.SerializerMethodField()

    class Meta:
        model = CustomerProfile
        fields = ['id', 'full_name', 'email', 'total_spent', 'joined_date', 'is_active']

    def get_total_spent(self, obj):
        return sum(order.total for order in obj.user.orders.all())

class AdminVendorSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.full_name')
    store_name = serializers.CharField(source='name')
    email = serializers.EmailField(source='user.email', read_only=True)
    joined_date = serializers.DateTimeField(source='user.joined_at', read_only=True)
    total_sales = serializers.SerializerMethodField()
    total_balance = serializers.SerializerMethodField()


    class Meta:
        model = VendorProfile
        fields = ['id', 'full_name', 'store_name', 'email', 'joined_date', 'is_active', 'verification_status', 'total_sales', 'total_balance']
    
    def get_total_sales(self, obj):
        return sum(order.total for order in obj.user.orders.all())
    def get_total_balance(self, obj):
        # Placeholder for actual balance calculation logic
        return sum(order.total for order in obj.user.orders.filter(status='delivered'))

class AdminCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'parent', 'image']
