from django.conf import settings


def community(request):
    """Cho base.html biết có hiện link 'Cộng đồng' trên thanh điều hướng hay không."""
    return {"community_enabled": settings.COMMUNITY_DEMO}
