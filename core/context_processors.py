from django.conf import settings
from django.templatetags.static import static


def site(request):
    unread = 0
    if request.user.is_authenticated:
        unread = request.user.notifications.filter(read=False).count()
    canonical_url = request.build_absolute_uri(request.path)
    og_default_image = request.build_absolute_uri(static("img/og-preview.png"))
    cookie_choice = request.COOKIES.get("grin_cookies", "")
    if cookie_choice not in ("accepted", "essential"):
        cookie_choice = ""
    return {
        "SITE_NAME": settings.SITE_NAME,
        "unread_count": unread,
        "canonical_url": canonical_url,
        "og_default_image": og_default_image,
        "cookie_choice": cookie_choice,
    }

