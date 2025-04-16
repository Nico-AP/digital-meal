from django.urls import path

from .views import SendReportLink
from .youtube import views as youtube_views
from .tiktok import views as tiktok_views


urlpatterns = [
    path(
        'youtube/class/<slug:url_id>',
        youtube_views.YouTubeReportClassroom.as_view(),
        name='youtube_class_report'
    ),  # slug:url_id relates to Classroom.url_id.
    path(
        'youtube/class/<slug:url_id>/individual/<slug:participant_id>',
        youtube_views.YouTubeReportIndividual.as_view(),
        name='youtube_individual_report'
    ),  # slug:url_id relates to Classroom.url_id.
    path(
        'youtube-example',
        youtube_views.YouTubeExampleReport.as_view(),
        name='youtube_example_report'
    ),
    path(
        'tiktok/class/<slug:url_id>/tiktok-report',
        tiktok_views.TikTokReportClassroom.as_view(),
        name='tiktok_class_report'
    ),  # slug:url_id relates to Classroom.url_id.
    path(
        'tiktok/class/<slug:url_id>/individual/<slug:participant_id>',
        tiktok_views.TikTokReportIndividual.as_view(),
        name='tiktok_individual_report'
    ),  # slug:url_id relates to Classroom.url_id.
    path(
        'tiktok-example',
        tiktok_views.TikTokExampleReport.as_view(),
        name='tiktok_example_report'
    ),
    path(
        'send-report-link',
        SendReportLink.as_view(),
        name='send_report_link'
    )
]
