from django.conf import settings


def site(request):
    unread = 0
    if request.user.is_authenticated:
        unread = request.user.notifications.filter(read=False).count()
    return {"SITE_NAME": settings.SITE_NAME, "unread_count": unread}
