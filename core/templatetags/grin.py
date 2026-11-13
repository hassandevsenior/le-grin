from urllib.parse import urlparse

from django import template

register = template.Library()


@register.filter
def host(url):
    """https://www.exemple.bf/page -> exemple.bf"""
    netloc = urlparse(url or "").netloc
    return netloc[4:] if netloc.startswith("www.") else netloc


@register.filter
def has(relation, user):
    """Vrai si `user` fait partie de la relation (déjà préchargée de préférence)."""
    if not getattr(user, "is_authenticated", False):
        return False
    return any(member.pk == user.pk for member in relation.all())
