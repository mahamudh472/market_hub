from apps.orders.models import Order
from apps.products.models import Product
from apps.vendor.models import VendorProfile
from django.db.models import Sum, F, FloatField, Q


vendor_status = VendorProfile.VerificationStatus

def get_dashboard_data():

    vendors = VendorProfile.objects.filter(
        Q(verification_status=vendor_status.APPROVED) | Q(verification_status=vendor_status.PENDING)
    )
    vendors_status = vendors.values('name', 'verification_status', 'user__full_name')[:5]  # Get the first 5 vendors with their status

    orders = Order.objects.filter(
        Q(status='completed') | Q(status='shipped') | Q(status='delivered') | Q(status='confirmed') | Q(status='pending')
    )  # Assuming 'completed' is the status for completed orders
    total_orders = orders.count()
    total_sales = orders.aggregate(total_sales=Sum('total'))['total_sales'] or 0
    recent_orders = orders.select_related('user').order_by('-created_at').values(
        'id', 'user__full_name', 'total', 'created_at', 'status', 'order_number'
    )[:5]  # Get the 5 most recent orders

    recommended_vendors = vendors.order_by('-recommended').values(
        'name', 'user__full_name', 'recommended'
    )


    approved_vendors = vendors.filter(verification_status=vendor_status.APPROVED).count()
    # TODO: Calculate total sales and commissions earned based on your business logic.
    commissions_earned = 0

    return {
        'verification_status': vendors_status,
        'approved_vendors': approved_vendors,
        'recommended_vendors': recommended_vendors,
        'total_orders': total_orders,
        'recent_orders': recent_orders,
        'total_sales': total_sales,
        'commissions_earned': commissions_earned,
    }
