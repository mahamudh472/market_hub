from rest_framework.permissions import BasePermission

class IsVendorOwner(BasePermission):
    """
    Custom permission to only allow vendors to access certain views.
    """

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'vendor'


class IsCustomerOwner(BasePermission):
    """Allow access only to authenticated customers."""

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'customer'
