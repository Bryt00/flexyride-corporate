class StaffRoleEnforcementMiddleware:
    """
    Ensures that authenticated users with SYSTEM_ADMIN or BROKER roles
    are immediately treated as active staff and superusers in Django Admin,
    eliminating 403 PermissionDenied errors across all session states.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, 'user', None) and request.user.is_authenticated:
            role = getattr(request.user, 'role', None)
            if role in ['SYSTEM_ADMIN', 'BROKER']:
                if not request.user.is_staff or not request.user.is_superuser:
                    request.user.is_staff = True
                    request.user.is_superuser = True
                    try:
                        from accounts.models import User
                        User.objects.filter(pk=request.user.pk).update(is_staff=True, is_superuser=True)
                    except Exception:
                        pass
        return self.get_response(request)
