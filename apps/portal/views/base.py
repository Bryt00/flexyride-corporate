"""Shared permission checks and predicates for Portal views."""
from accounts.models import User


def is_corporate(user):
    return user.is_authenticated and user.role in [User.Role.CUSTOMER, User.Role.EMPLOYEE_REQUESTER]


def is_broker(user):
    return user.is_authenticated and (
        user.role == User.Role.BROKER
        or user.role == User.Role.SYSTEM_ADMIN
        or user.is_superuser
    )


def is_provider(user):
    return user.is_authenticated and (
        user.role == User.Role.PROVIDER_ADMIN
        or user.role == User.Role.SYSTEM_ADMIN
        or user.is_superuser
    )


def is_admin(user):
    return user.is_authenticated and (
        user.role == User.Role.SYSTEM_ADMIN or user.is_superuser
    )


def can_view_request(user):
    return user.is_authenticated and (
        user.role in [User.Role.CUSTOMER, User.Role.EMPLOYEE_REQUESTER, User.Role.BROKER, User.Role.SYSTEM_ADMIN]
        or user.is_superuser
        or user.is_staff
    )
