from django.urls import path

from . import views


urlpatterns = [
    path(
        'class/<slug:url_id>/overview',
        views.YouTubeReportClassroom.as_view(),
        name='class_report'
    ),
    path(
        'class/<slug:url_id>/individual/<slug:participant_id>',
        views.YouTubeReportIndividual.as_view(),
        name='individual_report'
    ),  # slug:url_id relates to Classroom.url_id.
    path(
        'send-report-link',
        views.SendReportLink.as_view(),
        name='send_report_link'
    )
]
