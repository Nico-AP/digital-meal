from django.urls import include, path
from django.views.defaults import page_not_found

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
]

# DDM's login/logout names are stubbed out so reverse() always finds them.
# Placed after MDM patterns so that in SUBDOMAIN mode (MDM at root) the MDM
# login view wins; these stubs only fire when no MDM pattern has matched first.
ddm_auth_stubs = [
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
