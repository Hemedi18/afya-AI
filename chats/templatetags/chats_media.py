from django import template
from django.templatetags.static import static


register = template.Library()


@register.filter
def media_exists(file_field):
    if not file_field:
        return False

    try:
        name = getattr(file_field, 'name', '')
        storage = getattr(file_field, 'storage', None)
        if not name or storage is None:
            return False
        return storage.exists(name)
    except Exception:
        return False


@register.filter
def safe_media_url(file_field, fallback_path='img/fallbacks/community-media.svg'):
    if media_exists(file_field):
        try:
            return file_field.url
        except Exception:
            return static(fallback_path)
    return static(fallback_path)
