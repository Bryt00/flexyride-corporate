"""
Web Push Dispatcher & Notification Service for FlexyRide Corporate.
100% Free browser push notification delivery using standard W3C Push API & VAPID.
Also records system in-app notifications in notifications.Notification.
"""

import json
import logging
from django.conf import settings
from django.utils import timezone
from notifications.models import Notification, WebPushSubscription

logger = logging.getLogger(__name__)


def get_vapid_public_key():
    return getattr(settings, 'VAPID_PUBLIC_KEY', '')


def get_vapid_private_key():
    return getattr(settings, 'VAPID_PRIVATE_KEY', '')


def get_vapid_admin_email():
    return getattr(settings, 'VAPID_ADMIN_EMAIL', 'mailto:dispatch@flexyride.com')


def dispatch_notification(
    user=None,
    passenger_info=None,
    request_obj=None,
    title="FlexyRide Update",
    message="",
    notification_type=Notification.NotificationType.SYSTEM,
    url=None,
    data=None
):
    """
    Creates an in-app Notification record and pushes it to all registered
    Web Push subscriptions for this user.
    """
    notif = Notification.objects.create(
        recipient=user,
        passenger_info=passenger_info,
        request=request_obj,
        channel=Notification.Channel.PUSH if user and user.web_push_subscriptions.exists() else Notification.Channel.IN_APP,
        notification_type=notification_type,
        title=title,
        message=message,
        delivery_status=Notification.DeliveryStatus.SENT,
        sent_at=timezone.now()
    )

    # Deliver via Web Push if user has active browser push subscriptions
    if user:
        subs = user.web_push_subscriptions.all()
        for sub in subs:
            payload = {
                "title": title,
                "body": message,
                "icon": "/static/portal/img/logo.png",
                "badge": "/static/portal/img/badge.png",
                "url": url or "/portal/dashboard/",
                "tag": f"fr-{notif.id}",
                "data": data or {}
            }
            send_single_web_push(sub, payload)

    return notif


def send_single_web_push(subscription: WebPushSubscription, payload: dict):
    """
    Sends a push notification to a browser push endpoint using pywebpush if available,
    or logs delivery.
    """
    try:
        from pywebpush import webpush, WebPushException
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh,
                "auth": subscription.auth
            }
        }
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=get_vapid_private_key(),
            vapid_claims={"sub": get_vapid_admin_email()}
        )
        logger.info("Web push dispatched successfully to %s", subscription.endpoint[:40])
    except ImportError:
        # pywebpush not installed in environment; simulation mode
        logger.info("[WebPush Simulator] Sent browser push to %s: %s", subscription.endpoint[:40], payload.get("title"))
    except Exception as e:
        logger.warning("Failed to dispatch web push: %s", e)
