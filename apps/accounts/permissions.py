from rest_framework.permissions import BasePermission


from rest_framework import permissions


class IsCustomer(permissions.BasePermission):
    """Allows access only to Corporate Customer users."""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'CUSTOMER'
        )


# Backward compatibility alias
IsCustomerRep = IsCustomer


class IsBroker(permissions.BasePermission):
    """Allows access only to FlexyRide Broker staff."""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'BROKER'
        )


class IsProviderAdmin(permissions.BasePermission):
    """Allows access only to Provider Administrator users."""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'PROVIDER_ADMIN'
        )


class IsDriver(permissions.BasePermission):
    """Allows access only to Driver users."""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'DRIVER'
        )


class IsSystemAdmin(permissions.BasePermission):
    """Allows access only to System Administrator users."""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'SYSTEM_ADMIN'
        )


# Composite permissions for endpoints accessed by multiple roles
class IsBrokerOrProviderAdmin(permissions.BasePermission):
    """Allows access to Brokers OR Provider Admins."""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ('BROKER', 'PROVIDER_ADMIN')
        )


class IsBrokerOrCustomerRep(permissions.BasePermission):
    """Allows access to Brokers OR Corporate Customers."""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ('BROKER', 'CUSTOMER')
        )


class IsCorporateEmployee(permissions.BasePermission):
    """Allows access to any employee of a Corporate Customer."""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ('EMPLOYEE', 'EMPLOYEE_REQUESTER', 'CUSTOMER')
        )


class IsCustomerRepOrRequester(permissions.BasePermission):
    """Allows access to Corporate Customer OR Employee Requester users."""
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ('CUSTOMER', 'EMPLOYEE_REQUESTER')
        )


class IsBrokerOrAdmin(BasePermission):
    """Allows access to Broker OR System Admin users (internal FlexyRide staff)."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ('BROKER', 'SYSTEM_ADMIN')
        )


class CanViewCommercialData(BasePermission):
    """
    Protects commercially sensitive data (provider costs, margins) from customer exposure.
    Only Brokers and System Admins can view commercial data (US-49, US-108).
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in ('BROKER', 'SYSTEM_ADMIN')
        )


class IsOwnerOrBroker(BasePermission):
    """
    Object-level permission: allows access if user owns the object or is a broker/admin.
    Requires the view's queryset objects to have a 'requester' or 'user' field.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role in ('BROKER', 'SYSTEM_ADMIN'):
            return True
        # Check various ownership patterns
        if hasattr(obj, 'requester') and obj.requester == request.user:
            return True
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
        if hasattr(obj, 'paid_by') and obj.paid_by == request.user:
            return True
        if hasattr(obj, 'reported_by') and obj.reported_by == request.user:
            return True
        return False


class IsProviderOwnerOrBroker(BasePermission):
    """
    Object-level permission for provider-scoped resources.
    Provider admins can only access their own company's data.
    """

    def has_object_permission(self, request, view, obj):
        if request.user.role in ('BROKER', 'SYSTEM_ADMIN'):
            return True
        if request.user.role == 'PROVIDER_ADMIN':
            provider = getattr(obj, 'provider', None)
            if provider and hasattr(request.user, 'provider_admin_profile'):
                return provider == request.user.provider_admin_profile.company
        return False
