from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.urls.ddm_integration import ddm_patterns

base_urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("portability/", include("shared.portability.urls")),
]

debug_patterns = []
if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    debug_patterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    ) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    debug_patterns += debug_toolbar_urls()
    debug_patterns += [path("__reload__/", include("django_browser_reload.urls"))]

base_urlpatterns += ddm_patterns
base_urlpatterns += debug_patterns
