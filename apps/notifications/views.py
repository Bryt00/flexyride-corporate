"""Web push and in-app notification API endpoints."""
import json
from django.conf import settings
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from notifications.models import Notification, WebPushSubscription


@login_required
def webpush_subscribe_api(request):
    """Registers a browser push subscription for the logged-in user (100% Free Web Push)."""
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        data = json.loads(request.body)
        endpoint = data.get('endpoint')
        keys = data.get('keys', {})
        p256dh = keys.get('p256dh')
        auth = keys.get('auth')

        if not endpoint or not p256dh or not auth:
            return JsonResponse({"error": "Invalid subscription keys"}, status=400)

        sub, _ = WebPushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={
                'user': request.user,
                'p256dh': p256dh,
                'auth': auth,
                'user_agent': request.META.get('HTTP_USER_AGENT', '')[:255]
            }
        )
        return JsonResponse({"status": "ok", "id": sub.id})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
def notifications_api(request):
    """Returns active in-app notifications and unread count for the current user."""
    notifs = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:10]
    unread_count = Notification.objects.filter(recipient=request.user, read_at__isnull=True).count()
    items = []
    for n in notifs:
        items.append({
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.notification_type,
            "created_at": n.created_at.strftime("%b %d, %H:%M"),
            "read": bool(n.read_at)
        })
    return JsonResponse({
        "unread_count": unread_count,
        "notifications": items,
        "vapid_public_key": getattr(settings, 'VAPID_PUBLIC_KEY', '')
    })
