from django.urls import include, path

from mydigitalmeal.userflow import views

app_name = "userflow"
urlpatterns = [
    path(
        "",
        views.LandingPageView.as_view(),
        name="landing_page",
    ),
    path(
        "overview/",
        views.OverviewView.as_view(),
        name="overview",
    ),
    path("resume/<uuid:request_id>", views.UserflowResumeView.as_view(), name="resume"),
    path("reset/", views.UserflowResetView.as_view(), name="reset"),
    path(
        "portability/callback/",
        views.PortabilityCallbackRouterView.as_view(),
        name="portability_callback_router",
    ),
    path(
        "portability/auth-router/",
        views.PortabilityAuthRetryRouterView.as_view(),
        name="portability_auth_router",
    ),
    path(
        "",
        include("mydigitalmeal.profiles.urls", namespace="profiles"),
    ),
    path(
        "",
        include("mydigitalmeal.datadonation.urls", namespace="datadonation"),
    ),
    path(
        "",
        include("mydigitalmeal.questionnaire.urls", namespace="questionnaire"),
    ),
    path(
        "",
        include("mydigitalmeal.reports.urls", namespace="reports"),
    ),
    path(
        "",
        include("mydigitalmeal.studies.urls", namespace="studies"),
    ),
]
