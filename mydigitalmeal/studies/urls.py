from django.urls import path

from mydigitalmeal.studies import views

app_name = "studies"
urlpatterns = [
    path(
        "study/enroll/",
        views.StudyEnrollView.as_view(),
        name="enroll",
    ),
    path(
        "study/dua/",
        views.DownloadUploadView.as_view(),
        name="download_upload",
    ),
    path(
        "study/connect/",
        views.PortabilityEntryView.as_view(),
        name="port_tt_connect",
    ),
    path(
        "study/connect/await/",
        views.PortabilityWaitingView.as_view(),
        name="port_tt_await_data",
    ),
    path(
        "study/connect/check/",
        views.CheckDownloadAvailabilityView.as_view(),
        name="port_tt_check_data",
    ),
    path(
        "study/review/",
        views.PortabilityReviewView.as_view(),
        name="port_tt_review_data",
    ),
]
