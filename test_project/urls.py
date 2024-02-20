from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.documents import urls as wagtaildocs_urls


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('digital_meal.urls')),
    path('ddm/', include('ddm.urls')),
    path('ckeditor/', include('ckeditor_uploader.urls')),
    path('cms/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),
    path('', include('wagtail.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + \
                   static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
