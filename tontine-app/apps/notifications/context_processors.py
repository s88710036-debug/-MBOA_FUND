def notifications(request):
    """
    Context processor that adds unread notification count to every template context.
    """
    if not request.user.is_authenticated:
        return {"unread_notifications_count": 0, "unread_notifications": []}

    try:
        from apps.notifications.models import Notification
        unread = Notification.objects.filter(user=request.user, is_read=False)
        return {
            "unread_notifications_count": unread.count(),
            "unread_notifications": unread[:5],
        }
    except Exception:
        return {"unread_notifications_count": 0, "unread_notifications": []}
