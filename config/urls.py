from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.defaults import page_not_found


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('cookies/', include('cookie_consent.urls')),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
]

custom_ddm_patterns = [
    path(
        r'teilnahme/<slug:slug>/',
        include('ddm.participation.urls', namespace='ddm_participation')
    ),
    path(
        r'ddm/projects/',
        include('ddm.projects.urls', namespace='ddm_projects')
    ),
    path(
        r'ddm/projects/<slug:project_url_id>/questionnaire/',
        include('ddm.questionnaire.urls', namespace='ddm_questionnaire')
    ),
    path(
        r'ddm/projects/<slug:project_url_id>/data-donation/',
        include('ddm.datadonation.urls', namespace='ddm_datadonation')
    ),
    path(
        r'ddm/',
        include('ddm.logging.urls', namespace='ddm_logging')
    ),
    path(
        r'ddm/',
        include('ddm.auth.urls', namespace='ddm_auth')
    ),
    path(
        r'ddm-api/',
        include('ddm.apis.urls', namespace='ddm_apis')
    ),
    path(
        'login/',
        page_not_found,
        name='ddm_login'
    ),
    path(
        'logout/',
        page_not_found,
        name='ddm_logout'
    ),
]

urlpatterns += custom_ddm_patterns

# digital_meal.urls should be last (otherwise urls seem not to be properly loaded.)
urlpatterns += [
    path('', include('digital_meal.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + \
                   static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
