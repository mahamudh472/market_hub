from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import Role, User
from vendor.models import VendorProfile


class VendorVerificationWorkflowAPITest(APITestCase):
	def setUp(self):
		self.submit_url = reverse('profile_submit')
		self.my_store_url = reverse('store-detail')

		self.vendor_user = User.objects.create_user(
			email='vendor-flow@example.com',
			password='strong-pass',
			role=Role.VENDOR,
			full_name='Flow Vendor',
		)
		self.vendor_profile = self.vendor_user.vendor_profile

	def test_vendor_profile_auto_created_as_pending(self):
		self.assertIsNotNone(self.vendor_profile)
		self.assertEqual(self.vendor_profile.verification_status, VendorProfile.VerificationStatus.PENDING)
		self.assertFalse(self.vendor_profile.is_verified)

	def test_vendor_can_submit_and_resubmit_for_review(self):
		self.vendor_profile.verification_status = VendorProfile.VerificationStatus.REJECTED
		self.vendor_profile.save(update_fields=['verification_status'])

		self.client.force_authenticate(user=self.vendor_user)
		payload = {
			'name': 'Flow Vendor Updated',
			'contact_phone': '01711111111',
			'address': 'Dhaka',
		}

		response = self.client.patch(self.submit_url, payload, format='json')

		self.assertEqual(response.status_code, status.HTTP_200_OK)
		self.vendor_profile.refresh_from_db()
		self.assertEqual(self.vendor_profile.verification_status, VendorProfile.VerificationStatus.PENDING)
		self.assertIsNotNone(self.vendor_profile.last_submitted_at)
		self.assertEqual(response.data['status'], VendorProfile.VerificationStatus.PENDING)

	def test_blocked_vendor_cannot_resubmit(self):
		self.vendor_profile.verification_status = VendorProfile.VerificationStatus.BLOCKED
		self.vendor_profile.last_submitted_at = self.vendor_profile.created_at
		self.vendor_profile.save(update_fields=['verification_status', 'last_submitted_at'])

		self.client.force_authenticate(user=self.vendor_user)
		response = self.client.patch(self.submit_url, {'name': 'Try submit again'}, format='json')

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
		self.assertFalse(response.data['can_resubmit'])
		self.assertTrue(response.data['blocked'])
		self.assertEqual(response.data['status'], VendorProfile.VerificationStatus.BLOCKED)

	def test_pending_vendor_gets_not_verified_response_on_my_store(self):
		self.vendor_profile.verification_status = VendorProfile.VerificationStatus.PENDING
		self.vendor_profile.last_submitted_at = self.vendor_profile.created_at
		self.vendor_profile.save(update_fields=['verification_status', 'last_submitted_at'])

		self.client.force_authenticate(user=self.vendor_user)
		response = self.client.get(self.my_store_url)

		self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
		self.assertEqual(response.data['message'], 'Your vendor profile is not verified yet.')
		self.assertEqual(response.data['status'], VendorProfile.VerificationStatus.PENDING)
		self.assertIn('last_submitted_at', response.data)
