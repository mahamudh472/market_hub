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

from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from unittest.mock import patch, MagicMock

from products.models import (
    Product, ProductVariantType,
    ProductVariantOption, ProductVariant, Category
)
from .serializers import ProductCreateSerializer
from vendor.models import VendorProfile

User = get_user_model()


def make_request_with_vendor(vendor):
    """Helper: fake DRF request carrying a vendor user."""
    factory = APIRequestFactory()
    request = factory.post("/")
    request.user = MagicMock()
    request.user.vendorprofile = vendor
    return request


def base_payload(**overrides):
    """Minimal valid payload with no variants."""
    data = {
        "name": "Classic Tee",
        "description": "100% cotton tee",
        "price": "15.00",
        "stock": 100,
        # category FK is injected per-test after the object is created
    }
    data.update(overrides)
    return data


class ProductCreateSerializerTestCase(TestCase):

    # ── Fixtures ──────────────────────────────────────────────────────────────

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@mail.com", password="pass"
        )
        self.vendor = VendorProfile.objects.create(user=self.user)
        self.category = Category.objects.create(name="Apparel")
        self.request = make_request_with_vendor(self.vendor)

    def _serialize(self, payload):
        """Shortcut: build + validate serializer, return (serializer, is_valid)."""
        s = ProductCreateSerializer(
            data=payload, context={"request": self.request}
        )
        valid = s.is_valid()
        return s, valid

    # ── 1. Happy path — no variants ───────────────────────────────────────────

    def test_create_product_no_variants(self):
        payload = base_payload(category=self.category.pk)
        s, valid = self._serialize(payload)

        self.assertTrue(valid, s.errors)
        product = s.save()

        self.assertIsNotNone(product.pk)
        self.assertEqual(product.name, "Classic Tee")
        self.assertEqual(product.vendor, self.vendor)
        self.assertEqual(product.category, self.category)
        self.assertEqual(Product.objects.count(), 1)

    # ── 2. Happy path — with images ───────────────────────────────────────────

    def test_create_product_with_images(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        img1 = SimpleUploadedFile("a.jpg", b"img_a", content_type="image/jpeg")
        img2 = SimpleUploadedFile("b.jpg", b"img_b", content_type="image/jpeg")

        payload = base_payload(
            category=self.category.pk,
            images=[
                {"image": img1, "thumbnail": True},
                {"image": img2, "thumbnail": False},
            ],
        )
        s, valid = self._serialize(payload)
        self.assertTrue(valid, s.errors)
        product = s.save()

        self.assertEqual(product.images.count(), 2)
        self.assertTrue(product.images.filter(thumbnail=True).exists())

    # ── 3. Happy path — full variant tree ─────────────────────────────────────

    def test_create_product_with_variants(self):
        payload = base_payload(
            category=self.category.pk,
            stock=0,
            variant_types=[
                {"name": "Size",  "options": [{"value": "SM"}, {"value": "M"}]},
                {"name": "Color", "options": [{"value": "Red"}, {"value": "Blue"}]},
            ],
            variants=[
                {
                    "options": [
                        {"type": "Size", "value": "SM"},
                        {"type": "Color", "value": "Red"},
                    ],
                    "price": "14.00",
                    "stock": 10,
                },
                {
                    "options": [
                        {"type": "Size", "value": "M"},
                        {"type": "Color", "value": "Blue"},
                    ],
                    "price": "14.00",
                    "discount": "10.00",
                    "stock": 5,
                },
            ],
        )
        s, valid = self._serialize(payload)
        self.assertTrue(valid, s.errors)
        product = s.save()

        # variant types & options
        self.assertEqual(ProductVariantType.objects.filter(product=product).count(), 2)
        self.assertEqual(ProductVariantOption.objects.filter(variant_type__product=product).count(), 4)

        # variants
        self.assertEqual(ProductVariant.objects.filter(product=product).count(), 2)

        # M2M wired correctly
        sm_red = ProductVariant.objects.get(product=product, price=Decimal("14.00"), discount=None)
        option_labels = {(o.variant_type.name, o.value) for o in sm_red.options.all()}
        self.assertIn(("Size", "SM"), option_labels)
        self.assertIn(("Color", "Red"), option_labels)

    # ── 4. discounted_price property ─────────────────────────────────────────

    def test_discounted_price_on_product(self):
        payload = base_payload(category=self.category.pk, discount="20.00")
        s, valid = self._serialize(payload)
        self.assertTrue(valid, s.errors)
        product = s.save()

        expected = (1 - Decimal("20.00") / 100) * Decimal("15.00")
        self.assertAlmostEqual(product.discounted_price, expected, places=2)

    def test_discounted_price_no_discount(self):
        payload = base_payload(category=self.category.pk)
        s, _ = self._serialize(payload)
        product = s.save()
        self.assertEqual(product.discounted_price, Decimal("15.00"))

    # ── 5. Validation — missing required fields ───────────────────────────────

    def test_missing_name_is_invalid(self):
        payload = base_payload(category=self.category.pk)
        del payload["name"]
        _, valid = self._serialize(payload)
        self.assertFalse(valid)

    def test_missing_category_is_invalid(self):
        _, valid = self._serialize(base_payload())   # no category key
        self.assertFalse(valid)

    # ── 6. Validation — variants without variant_types ────────────────────────

    def test_variants_without_variant_types_raises(self):
        payload = base_payload(
            category=self.category.pk,
            variants=[
                {
                    "options": [{"type": "Size", "value": "SM"}],
                    "price": "10.00",
                    "stock": 5,
                }
            ],
        )
        _, valid = self._serialize(payload)
        self.assertFalse(valid)
        self.assertIn(
            "variant_types",
            str(next(iter(_.errors.values())) if not isinstance(_.errors, list) else _.errors).lower()
            if False else str(_.errors).lower(),
        )

    # ── 7. Validation — variant references unknown type ──────────────────────

    def test_variant_unknown_type_raises(self):
        payload = base_payload(
            category=self.category.pk,
            variant_types=[
                {"name": "Size", "options": [{"value": "SM"}]},
            ],
            variants=[
                {
                    "options": [{"type": "NonExistent", "value": "SM"}],
                    "price": "10.00",
                    "stock": 5,
                }
            ],
        )
        _, valid = self._serialize(payload)
        self.assertFalse(valid)

    # ── 8. Validation — variant references unknown option value ──────────────

    def test_variant_unknown_option_value_raises(self):
        payload = base_payload(
            category=self.category.pk,
            variant_types=[
                {"name": "Size", "options": [{"value": "SM"}]},
            ],
            variants=[
                {
                    "options": [{"type": "Size", "value": "XXXL"}],  # not declared
                    "price": "10.00",
                    "stock": 5,
                }
            ],
        )
        _, valid = self._serialize(payload)
        self.assertFalse(valid)

    # ── 9. Vendor is always taken from request, not payload ───────────────────

    def test_vendor_assigned_from_request_not_payload(self):
        other_user = User.objects.create_user(username="other", password="pass")
        other_vendor = VendorProfile.objects.create(user=other_user)

        payload = base_payload(category=self.category.pk)
        # Even if someone sneaks a vendor field in, it should be ignored
        payload["vendor"] = other_vendor.pk

        s, valid = self._serialize(payload)
        self.assertTrue(valid, s.errors)
        product = s.save()

        self.assertEqual(product.vendor, self.vendor)   # original request vendor wins
        self.assertNotEqual(product.vendor, other_vendor)

    # ── 10. Negative price / stock rejected ───────────────────────────────────

    def test_negative_stock_on_variant_is_invalid(self):
        payload = base_payload(
            category=self.category.pk,
            variant_types=[{"name": "Size", "options": [{"value": "SM"}]}],
            variants=[
                {
                    "options": [{"type": "Size", "value": "SM"}],
                    "price": "10.00",
                    "stock": -1,   # invalid
                }
            ],
        )
        _, valid = self._serialize(payload)
        self.assertFalse(valid)
