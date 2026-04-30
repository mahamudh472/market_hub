from rest_framework import serializers
from .models import User, CustomerProfile, UserAddress
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .utils import send_otp_email
from apps.orders.serializers import SimpleOrderSerializer

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        print("user:", user)
        print("is_active:", user.is_active)
        if user and not user.is_active:
            send_otp_email(user)
            raise serializers.ValidationError({
                'detail': 'Account is not active. An OTP has been sent to your email for verification.',
            })

        data['role'] = user.role
        data['vendor_profile_status'] = None
        data['vendor_last_submitted_at'] = None

        if user.role == 'vendor':
            vendor_profile = getattr(user, 'vendor_profile', None)
            if vendor_profile:
                data['vendor_profile_status'] = vendor_profile.verification_status
                data['vendor_last_submitted_at'] = vendor_profile.last_submitted_at

        return data

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'role', 'email', 'password', 'phone_number']

    def validate_role(self, value):
        if value not in ['customer', 'vendor']:
            raise serializers.ValidationError("Role must be either 'customer' or 'vendor'")
        return value

    def create(self, validated_data):
        print("Creating user with data:", validated_data)
        user = User.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data.get('full_name', ''),
            role=validated_data.get('role', 'customer'),
            phone_number=validated_data.get('phone_number', '')
        )
        user.set_password(validated_data['password'])
        user.is_active = False  # User will be activated after email verification
        user.save()
        
        return user
    

class VerifyEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)

class ResetPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp = serializers.CharField(max_length=6)
    new_password = serializers.CharField(write_only=True)

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("New passwords do not match")
        return data
    
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = ['password', 'groups', 'user_permissions']
        read_only_fields = ['id', 'email', 'joined_at', 'last_login', 'role', 'is_active', 'is_staff', 'is_superuser']

class CustomerProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    recent_orders = serializers.SerializerMethodField()
    total_orders = serializers.IntegerField(source='user.orders.count', read_only=True)
    total_saved_addresses = serializers.IntegerField(source='user.addresses.count', read_only=True)

    class Meta:
        model = CustomerProfile
        fields = '__all__'
        read_only_fields = ['user']

    def get_recent_orders(self, obj):
        orders = obj.user.orders.all().order_by('-created_at')[:5]
        return SimpleOrderSerializer(orders, many=True).data


class UserAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAddress
        fields = [
            'id',
            'label',
            'full_name',
            'phone_number',
            'address',
            'landmark',
            'city',
            'zone',
            'area',
            'postal_code',
            'country',
            'is_default_delivery',
            'is_default_billing',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate(self, attrs):
        city = attrs.get('city')
        zone = attrs.get('zone')

        # Prevent mismatched city/zone selections from being saved.
        if city and zone and zone.city_id != city.city_id:
            raise serializers.ValidationError({'zone': 'Selected zone does not belong to the selected city.'})

        return attrs

    def create(self, validated_data):
        return UserAddress.objects.create(user=self.context['request'].user, **validated_data)


