from django.urls import path

from . import views


urlpatterns = [
    path(
        'class/<int:pk>/overview',  # int:pk relates to ID of classroom.
        views.ClassroomReportYouTube.as_view(),
        name='class_report'
    ),
    path(
        'class/<int:pk>/individual/<slug:participant_id>',  # int:pk relates to ID of classroom.
        views.IndividualReportYouTube.as_view(),
        name='individual_report'
    ),
    path(
        'send-report-link',
        views.SendReportLink.as_view(),
        name='send_report_link'
    )
]
