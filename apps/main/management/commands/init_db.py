"""
Management command: init_db
===========================
Adds a batch of realistic-looking dummy data on every run.
Run it multiple times to keep growing the database.

Usage:
    python manage.py init_db
    python manage.py init_db --users 5 --products 20
"""

import random
import string
import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone


# ---------------------------------------------------------------------------
# Word banks (no third-party deps)
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Rahim", "Karim", "Salma", "Nadia", "Hasan", "Parisa", "Tariq",
    "Ahmed", "Fatima", "Omar", "Layla", "Yusuf", "Aisha", "Bilal",
    "Sana", "Imran", "Riya", "Dev", "Priya", "Arman", "Zara", "Nabil",
    "Sofia", "Lucas", "Emma", "James", "Olivia", "Noah", "Ava", "Liam",
]

LAST_NAMES = [
    "Khan", "Rahman", "Islam", "Hossain", "Chowdhury", "Ahmed", "Ali",
    "Sheikh", "Malik", "Patel", "Singh", "Das", "Roy", "Sen", "Bose",
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis",
]

CITIES = [
    "Dhaka", "Chittagong", "Sylhet", "Rajshahi", "Khulna", "Barisal",
    "Mymensingh", "Comilla", "Narayanganj", "Gazipur",
]

COUNTRIES = ["Bangladesh", "India", "Pakistan", "Sri Lanka"]

CATEGORY_DATA = [
    # (name, [child_names])
    ("Electronics", ["Smartphones", "Laptops", "Tablets", "Headphones", "Smart Watches", "Cameras"]),
    ("Clothing", ["Men's Wear", "Women's Wear", "Kids' Wear", "Accessories", "Footwear"]),
    ("Home & Garden", ["Furniture", "Kitchen", "Bedding", "Garden Tools", "Lighting"]),
    ("Books", ["Fiction", "Non-Fiction", "Science", "Technology", "Children's Books"]),
    ("Sports", ["Outdoor Sports", "Gym Equipment", "Cycling", "Swimming", "Cricket"]),
    ("Food & Grocery", ["Snacks", "Beverages", "Dairy", "Bakery", "Organic"]),
    ("Beauty", ["Skincare", "Haircare", "Makeup", "Fragrances", "Personal Care"]),
    ("Toys", ["Board Games", "Action Figures", "Educational Toys", "Dolls", "Puzzles"]),
]

ADJECTIVES = [
    "Premium", "Ultra", "Classic", "Pro", "Lite", "Elite",
    "Smart", "Super", "Mega", "Eco", "Luxury", "Compact",
]

NOUNS = [
    "Gadget", "Device", "Kit", "Set", "Bundle", "Pack",
    "Collection", "Series", "Edition", "Model", "Unit", "Item",
]

VENDOR_NAMES = [
    "TechMart", "StyleHub", "FreshDeals", "HomeWorld", "BookNest",
    "SportZone", "GreenStore", "GadgetBox", "UrbanStyle", "EasyShop",
    "QuickBuy", "TopTrend", "MegaMart", "ValueMall", "SmartChoice",
]

VARIANT_TYPES = {
    "Size": ["XS", "S", "M", "L", "XL", "XXL", "XXXL"],
    "Color": ["Red", "Blue", "Green", "Black", "White", "Yellow", "Pink", "Grey"],
    "Storage": ["32GB", "64GB", "128GB", "256GB", "512GB"],
    "RAM": ["4GB", "8GB", "16GB", "32GB"],
}

REVIEW_COMMENTS = [
    "Great product! Highly recommend.",
    "Good quality for the price.",
    "Exactly as described. Fast delivery.",
    "Very happy with this purchase.",
    "Solid build, works perfectly.",
    "Better than expected. Will buy again.",
    "Nice product but packaging could be better.",
    "Decent quality. Does the job.",
    "Love it! A must-buy.",
    "Average product, nothing special.",
    "Good value for money.",
    "Fast shipping & great quality.",
]

BANNER_TITLES = [
    "Summer Sale - Up to 50% Off!",
    "New Arrivals - Shop Now",
    "Flash Deal - Today Only",
    "Exclusive Member Offers",
    "Weekend Mega Sale",
    "Buy 2 Get 1 Free",
]

DELIVERY_CHARGE_DATA = [
    ("Standard Delivery", "3-5 business days", 60, 1500),
    ("Express Delivery", "1-2 business days", 120, 3000),
    ("Free Delivery", "7-10 business days", 0, None),
]

VOUCHER_DATA = [
    ("SAVE10", "10% off on all orders", "percentage", 10, 500, 500),
    ("FLAT50", "Flat BDT 50 off", "fixed", 50, None, 200),
    ("SUMMER20", "Summer sale 20% off", "percentage", 20, 800, 1000),
    ("NEWUSER", "New user 15% off", "percentage", 15, 300, 0),
    ("FLASH30", "Flash sale 30% off", "percentage", 30, 1000, 2000),
]

ORDER_STATUSES = ["pending", "confirmed", "processing", "shipped", "delivered"]
PAYMENT_METHODS = ["cod", "card", "mobile_banking", "online"]
PAYMENT_STATUSES = ["pending", "paid", "paid", "paid"]  # weighted toward paid


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rand_str(n=6):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=n))


def rand_email():
    return f"{random.choice(FIRST_NAMES).lower()}.{rand_str(4)}@example.com"


def rand_phone():
    return f"01{random.randint(3, 9)}{random.randint(10000000, 99999999)}"


def rand_price(low=50, high=5000):
    return Decimal(str(round(random.uniform(low, high), 2)))


def rand_discount():
    """Return a discount percentage (max_digits=3, decimal_places=2 → 0.00–9.99) or None.

    The model stores the *raw percentage*, e.g. 5.00 means 5 %.
    The discounted_price property computes: price * (1 - discount / 100).
    SQLite accepts out-of-range values silently; Django's ORM converter then
    raises InvalidOperation.  We must stay within 0.00–9.99.
    """
    if random.random() > 0.5:
        return Decimal(str(random.choice([1, 2, 3, 4, 5, 6, 7, 8, 9])))
    return None


def past_dt(days=365):
    return timezone.now() - timedelta(days=random.randint(1, days))


def future_dt(days=365):
    return timezone.now() + timedelta(days=random.randint(30, days))


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = (
        "Populate the database with dummy data. "
        "Every run adds more records — safe to call repeatedly."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--users", type=int, default=3,
            help="Number of new regular users to create per run (default: 3)",
        )
        parser.add_argument(
            "--vendors", type=int, default=2,
            help="Number of new vendor users to create per run (default: 2)",
        )
        parser.add_argument(
            "--products", type=int, default=10,
            help="Number of new products to create per run (default: 10)",
        )
        parser.add_argument(
            "--orders", type=int, default=5,
            help="Number of new orders to create per run (default: 5)",
        )

    # ------------------------------------------------------------------

    def handle(self, *args, **options):
        n_users = options["users"]
        n_vendors = options["vendors"]
        n_products = options["products"]
        n_orders = options["orders"]

        self.stdout.write(self.style.MIGRATE_HEADING("=== init_db: adding dummy data ==="))

        self._ensure_delivery_charges()
        self._ensure_vouchers()
        categories = self._ensure_categories()

        users = self._create_users(n_users)
        vendors = self._create_vendors(n_vendors)
        all_vendors = list(self._get_all_vendors())

        if not all_vendors:
            self.stdout.write(self.style.WARNING("No vendors found — skipping products/orders."))
            return

        products = self._create_products(n_products, all_vendors, categories)
        all_products = list(self._get_all_products())

        if all_products:
            self._add_reviews(all_products, users + self._get_existing_users())
            self._add_cart_items(all_products, users + self._get_existing_users())
            self._add_wishlist_items(all_products, users + self._get_existing_users())

        all_users = users + self._get_existing_users()
        if all_users and all_products:
            self._create_orders(n_orders, all_users, all_products, all_vendors)

        self.stdout.write(self.style.SUCCESS("Done! New rows added successfully."))

    # ------------------------------------------------------------------
    # Delivery Charges
    # ------------------------------------------------------------------

    def _ensure_delivery_charges(self):
        from apps.main.models import DeliveryCharge

        created = 0
        for name, desc, charge, min_amount in DELIVERY_CHARGE_DATA:
            obj, was_created = DeliveryCharge.objects.get_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "charge": Decimal(str(charge)),
                    "min_order_amount": Decimal(str(min_amount)) if min_amount else None,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(f"  Delivery charges ensured (+{created} new)")

    # ------------------------------------------------------------------
    # Vouchers
    # ------------------------------------------------------------------

    def _ensure_vouchers(self):
        from apps.cart.models import Voucher

        created = 0
        now = timezone.now()
        for code, desc, dtype, value, max_disc, min_order in VOUCHER_DATA:
            obj, was_created = Voucher.objects.get_or_create(
                code=code,
                defaults={
                    "description": desc,
                    "discount_type": dtype,
                    "discount_value": Decimal(str(value)),
                    "max_discount_amount": Decimal(str(max_disc)) if max_disc else None,
                    "min_order_amount": Decimal(str(min_order)),
                    "usage_limit": random.randint(50, 500),
                    "per_user_limit": 2,
                    "valid_from": now - timedelta(days=10),
                    "valid_until": now + timedelta(days=180),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(f"  Vouchers ensured (+{created} new)")

    # ------------------------------------------------------------------
    # Categories
    # ------------------------------------------------------------------

    def _ensure_categories(self):
        from apps.products.models import Category

        all_leaf_categories = []
        for parent_name, children in CATEGORY_DATA:
            parent, _ = Category.objects.get_or_create(name=parent_name)
            for child_name in children:
                child, _ = Category.objects.get_or_create(
                    name=child_name, defaults={"parent": parent}
                )
                all_leaf_categories.append(child)

        self.stdout.write(f"  Categories ensured ({Category.objects.count()} total)")
        return all_leaf_categories

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def _create_users(self, count):
        from apps.accounts.models import User, UserAddress

        created_users = []
        for _ in range(count):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f"{first.lower()}.{last.lower()}.{rand_str(4)}@example.com"

            user = User.objects.create(
                email=email,
                username=f"{first.lower()}{rand_str(3)}",
                full_name=f"{first} {last}",
                phone_number=rand_phone(),
                gender=random.choice(["male", "female", "other"]),
                age=random.randint(18, 55),
                is_active=True,
                is_staff=False,
                password=make_password("password123"),
            )

            # Add 1-2 addresses
            for i in range(random.randint(1, 2)):
                UserAddress.objects.create(
                    user=user,
                    label=random.choice(["home", "work", "other"]),
                    full_name=user.full_name,
                    phone_number=rand_phone(),
                    address_line1=f"{random.randint(1, 999)}, {rand_str(5).capitalize()} Street",
                    city=random.choice(CITIES),
                    state=random.choice(CITIES),
                    postal_code=str(random.randint(1000, 9999)),
                    country=random.choice(COUNTRIES),
                    is_default=(i == 0),
                )

            created_users.append(user)

        self.stdout.write(f"  Created {len(created_users)} new user(s)")
        return created_users

    def _get_existing_users(self):
        from apps.accounts.models import User
        return list(User.objects.filter(is_staff=False, vendor_profile__isnull=True))

    # ------------------------------------------------------------------
    # Vendors
    # ------------------------------------------------------------------

    def _create_vendors(self, count):
        from apps.accounts.models import User
        from apps.vendor.models import VendorProfile

        created_vendors = []
        for _ in range(count):
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            email = f"vendor.{first.lower()}.{rand_str(4)}@shop.com"

            user = User.objects.create(
                email=email,
                username=f"vendor_{rand_str(5)}",
                full_name=f"{first} {last}",
                phone_number=rand_phone(),
                is_active=True,
                is_staff=False,
                password=make_password("vendorpass123"),
            )

            vendor_name = f"{random.choice(VENDOR_NAMES)} {rand_str(3).upper()}"
            vendor = VendorProfile.objects.create(
                user=user,
                name=vendor_name,
                description=f"Quality products from {vendor_name}.",
                contact_email=email,
                contact_phone=rand_phone(),
                address=f"{random.randint(1, 200)}, Commerce Road",
                city=random.choice(CITIES),
                country=random.choice(COUNTRIES),
                is_verified=random.choice([True, False]),
                is_active=True,
                avg_rating=Decimal(str(round(random.uniform(3.0, 5.0), 2))),
                total_reviews=random.randint(0, 200),
            )
            created_vendors.append(vendor)

        self.stdout.write(f"  Created {len(created_vendors)} new vendor(s)")
        return created_vendors

    def _get_all_vendors(self):
        from apps.vendor.models import VendorProfile
        return VendorProfile.objects.filter(is_active=True)

    # ------------------------------------------------------------------
    # Products
    # ------------------------------------------------------------------

    def _create_products(self, count, vendors, categories):
        from apps.products.models import (
            Product, ProductVariant, ProductVariantOption, ProductVariantType,
        )

        created = []
        for _ in range(count):
            vendor = random.choice(vendors)
            category = random.choice(categories)
            adj = random.choice(ADJECTIVES)
            noun = random.choice(NOUNS)
            name = f"{adj} {category.name} {noun} {rand_str(3).upper()}"

            price = rand_price(100, 8000)
            discount = rand_discount()

            product = Product.objects.create(
                vendor=vendor,
                name=name,
                description=(
                    f"This is the {name}. A top-quality product from {vendor.name}. "
                    f"Perfect for everyday use. Available now at an unbeatable price."
                ),
                price=price,
                discount=discount,
                stock=random.randint(5, 200),
                category=category,
                product_details=(
                    f"Material: High-quality composite\n"
                    f"Weight: {round(random.uniform(0.1, 5.0), 1)} kg\n"
                    f"Dimensions: {random.randint(5, 50)}×{random.randint(5, 40)}×{random.randint(2, 30)} cm\n"
                    f"Warranty: {random.choice([6, 12, 24])} months"
                ),
                return_policy="7-day return policy. Item must be unused and in original packaging.",
            )

            # Add 1-2 variant types (50% chance)
            if random.random() > 0.5:
                chosen_types = random.sample(list(VARIANT_TYPES.keys()), k=random.randint(1, 2))
                type_option_map = {}

                for vtype_name in chosen_types:
                    vtype = ProductVariantType.objects.create(product=product, name=vtype_name)
                    options_values = random.sample(VARIANT_TYPES[vtype_name], k=random.randint(2, 4))
                    options = [
                        ProductVariantOption.objects.create(variant_type=vtype, value=v)
                        for v in options_values
                    ]
                    type_option_map[vtype] = options

                # Create variants as combinations
                type_keys = list(type_option_map.keys())
                if len(type_keys) == 1:
                    for opt in type_option_map[type_keys[0]]:
                        variant = ProductVariant.objects.create(
                            product=product,
                            price=price + rand_price(-50, 200),
                            discount=rand_discount(),
                            stock=random.randint(0, 50),
                        )
                        variant.options.set([opt])
                elif len(type_keys) == 2:
                    for opt1 in type_option_map[type_keys[0]]:
                        for opt2 in type_option_map[type_keys[1]]:
                            variant = ProductVariant.objects.create(
                                product=product,
                                price=price + rand_price(-50, 300),
                                discount=rand_discount(),
                                stock=random.randint(0, 50),
                            )
                            variant.options.set([opt1, opt2])

            created.append(product)

        self.stdout.write(f"  Created {len(created)} new product(s)")
        return created

    def _get_all_products(self):
        from apps.products.models import Product
        return list(Product.objects.all())

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------

    def _add_reviews(self, products, users):
        from apps.products.models import ProductReview

        if not users:
            return

        count = 0
        sample_products = random.sample(products, k=min(len(products), 5))
        for product in sample_products:
            sample_users = random.sample(users, k=min(len(users), 3))
            for user in sample_users:
                # Avoid duplicate (product, user) review if it already exists
                if not ProductReview.objects.filter(product=product, user=user).exists():
                    ProductReview.objects.create(
                        product=product,
                        user=user,
                        rating=random.randint(2, 5),
                        comment=random.choice(REVIEW_COMMENTS),
                    )
                    count += 1

        self.stdout.write(f"  Added {count} new review(s)")

    # ------------------------------------------------------------------
    # Cart items
    # ------------------------------------------------------------------

    def _add_cart_items(self, products, users):
        from apps.cart.models import Cart, CartItem

        if not users:
            return

        count = 0
        sample_users = random.sample(users, k=min(len(users), 4))
        for user in sample_users:
            cart, _ = Cart.objects.get_or_create(user=user)
            sample_products = random.sample(products, k=min(len(products), random.randint(1, 4)))
            for product in sample_products:
                variant = product.variants.order_by("?").first()
                if not CartItem.objects.filter(cart=cart, product=product, variant=variant).exists():
                    CartItem.objects.create(
                        cart=cart,
                        product=product,
                        variant=variant,
                        quantity=random.randint(1, 5),
                    )
                    count += 1

        self.stdout.write(f"  Added {count} new cart item(s)")

    # ------------------------------------------------------------------
    # Wishlist
    # ------------------------------------------------------------------

    def _add_wishlist_items(self, products, users):
        from apps.main.models import Wishlist

        if not users:
            return

        count = 0
        sample_users = random.sample(users, k=min(len(users), 4))
        for user in sample_users:
            sample_products = random.sample(products, k=min(len(products), random.randint(1, 5)))
            for product in sample_products:
                obj, created = Wishlist.objects.get_or_create(user=user, product=product)
                if created:
                    count += 1

        self.stdout.write(f"  Added {count} new wishlist item(s)")

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def _create_orders(self, count, users, products, vendors):
        from apps.accounts.models import UserAddress
        from apps.cart.models import Voucher
        from apps.orders.models import Order, OrderItem, Payment

        vouchers = list(Voucher.objects.filter(is_active=True))
        created = 0

        for _ in range(count):
            user = random.choice(users)
            address = UserAddress.objects.filter(user=user).first()

            # Random items 1-4
            order_products = random.sample(products, k=min(len(products), random.randint(1, 4)))
            subtotal = Decimal("0")
            items_data = []
            for product in order_products:
                variant = product.variants.order_by("?").first()
                unit_price = variant.discounted_price if variant else product.discounted_price
                qty = random.randint(1, 3)
                total = Decimal(str(unit_price)) * qty
                subtotal += total
                items_data.append((product, variant, unit_price, qty, total))

            voucher = random.choice(vouchers) if vouchers and random.random() > 0.6 else None
            voucher_discount = Decimal("0")
            if voucher:
                voucher_discount = voucher.calculate_discount(subtotal)

            tax = ((subtotal - voucher_discount) * Decimal("0.05")).quantize(Decimal("0.01"))
            delivery_charge = Decimal(str(random.choice([0, 60, 120])))
            total = subtotal - voucher_discount + tax + delivery_charge

            status = random.choice(ORDER_STATUSES)

            delivery_snapshot = None
            if address:
                delivery_snapshot = {
                    "full_name": address.full_name,
                    "phone_number": address.phone_number,
                    "address_line1": address.address_line1,
                    "city": address.city,
                    "country": address.country,
                    "postal_code": address.postal_code,
                }

            order = Order.objects.create(
                user=user,
                delivery_address=address,
                delivery_address_snapshot=delivery_snapshot,
                voucher_code=voucher.code if voucher else None,
                voucher_discount=voucher_discount,
                subtotal=subtotal,
                tax=tax,
                delivery_charge=delivery_charge,
                total=total,
                status=status,
            )

            for product, variant, unit_price, qty, total_price in items_data:
                variant_details = None
                if variant:
                    variant_details = {
                        o.variant_type.name: o.value
                        for o in variant.options.select_related("variant_type").all()
                    }
                OrderItem.objects.create(
                    order=order,
                    vendor=product.vendor,
                    product=product,
                    variant=variant,
                    product_name=product.name,
                    variant_details=variant_details,
                    unit_price=unit_price,
                    quantity=qty,
                    total_price=total_price,
                    status=status if status in ["delivered", "shipped"] else "pending",
                )

            # Payment
            pay_status = random.choice(PAYMENT_STATUSES)
            Payment.objects.create(
                order=order,
                method=random.choice(PAYMENT_METHODS),
                status=pay_status,
                amount=total,
                transaction_id=f"TXN-{rand_str(12).upper()}" if pay_status == "paid" else None,
                paid_at=timezone.now() - timedelta(hours=random.randint(1, 720)) if pay_status == "paid" else None,
            )

            created += 1

        self.stdout.write(f"  Created {created} new order(s)")
