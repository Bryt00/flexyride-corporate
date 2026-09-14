from django.conf import settings

def google_maps(request):
    """
    Exposes the Google Maps API key to all templates.
    """
    return {
        'GOOGLE_MAPS_API_KEY': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
    }


def corporate_context(request):
    """
    Exposes corporate company brand, logo, and provider context globally to templates.
    """
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}

    context = {}
    from accounts.models import User, ProviderCompany

    if request.user.role in [User.Role.CUSTOMER, User.Role.EMPLOYEE_REQUESTER]:
        profile = getattr(request.user, 'employee_profile', None)
        if profile and profile.company:
            context['company'] = profile.company
    elif request.user.role == User.Role.PROVIDER_ADMIN:
        provider = ProviderCompany.objects.filter(email=request.user.email).first() or ProviderCompany.objects.first()
        if provider:
            context['provider_company'] = provider
            context['company'] = provider

    return context

