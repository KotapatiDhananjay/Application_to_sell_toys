"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.generic import TemplateView

from apps.core.views import health_check


def api_root(request):
    return JsonResponse(
        {"name": "Toy Store API", "health": "/api/health/", "admin": "/admin/"}
    )


urlpatterns = [
    path("", TemplateView.as_view(template_name="index.html"), name="index"),
    path("admin/", admin.site.urls),
    path("api/health/", health_check, name="health-check"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.catalog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)