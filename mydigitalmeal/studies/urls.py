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
        "study/dl-ul/",
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
    path(
        "study/questionnaire/",
        views.StudyQuestionnaireView.as_view(),
        name="questionnaire",
    ),
    path(
        "study/debriefing/",
        views.StudyDebriefingView.as_view(),
        name="debriefing",
    ),
    path(
        "study/report/<slug:participant_id>/",
        views.StudyReportView.as_view(),
        name="report",
    ),
    path(
        "study/report/statistics/<slug:participant_id>/",
        views.StudyStatisticsView.as_view(),
        name="tiktok_statistics",
    ),
]
