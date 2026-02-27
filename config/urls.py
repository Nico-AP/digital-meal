from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.defaults import page_not_found

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("ckeditor5/", include("django_ckeditor_5.urls")),
]

ddm_patterns = [
    path(
        r"teilnahme/<slug:slug>/",
        include("ddm.participation.urls", namespace="ddm_participation"),
    ),
    path(r"ddm/projects/", include("ddm.projects.urls", namespace="ddm_projects")),
    path(
        r"ddm/projects/<slug:project_url_id>/questionnaire/",
        include("ddm.questionnaire.urls", namespace="ddm_questionnaire"),
    ),
    path(
        r"ddm/projects/<slug:project_url_id>/data-donation/",
        include("ddm.datadonation.urls", namespace="ddm_datadonation"),
    ),
    path(r"logs/", include("ddm.logging.urls", namespace="ddm_logging")),
    path(r"ddm/", include("ddm.auth.urls", namespace="ddm_auth")),
    path(r"ddm-api/", include("ddm.apis.urls", namespace="ddm_apis")),
    path(
        "login/",
        page_not_found,
        kwargs={"exception": Exception("Page not Found")},
        name="ddm_login",
    ),
    path(
        "logout/",
        page_not_found,
        kwargs={"exception": Exception("Page not Found")},
        name="ddm_logout",
    ),
]

urlpatterns += ddm_patterns

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    # Note: Did not work when placed in the settings.DEBUG block at the end.
    urlpatterns += debug_toolbar_urls()
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]

urlpatterns += [
    path("portability/", include("shared.portability.urls")),
    path("my/", include("mydigitalmeal.core.urls")),
    # digital_meal.urls should be last (otherwise urls seem not to be properly loaded.)
    path("", include("digital_meal.core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.STATIC_URL, document_root=settings.STATIC_ROOT
    ) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
