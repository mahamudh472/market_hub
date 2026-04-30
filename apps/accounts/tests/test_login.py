from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, User
from apps.vendor.models import VendorProfile


class LoginAPITest(APITestCase):
    def setUp(self):
        self.login_url = reverse('login', kwargs={'user_type': 'vendor'})
        self.password = 'strong-pass-123'

        self.vendor = User.objects.create_user(
            email='login-vendor@example.com',
            password=self.password,
            role=Role.VENDOR,
            full_name='Login Vendor',
            is_active=True,
        )
        self.vendor_profile = self.vendor.vendor_profile
        self.vendor_profile.verification_status = VendorProfile.VerificationStatus.REJECTED
        self.vendor_profile.save(update_fields=['verification_status'])

    def test_vendor_login_includes_vendor_profile_status(self):
        response = self.client.post(
            self.login_url,
            {
                'email': self.vendor.email,
                'password': self.password,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertEqual(response.data.get('vendor_profile_status'), VendorProfile.VerificationStatus.REJECTED)
