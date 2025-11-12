from django.urls import path

import digital_meal.reports.views.tiktok as tiktok_views
import digital_meal.reports.views.youtube as youtube_views
from .views.base import ReportExpired, SendReportLink

urlpatterns = [
    path(
        'report-expired',
        ReportExpired.as_view(),
        name='report_expired'
    ),
    path(
        'send-report-link',
        SendReportLink.as_view(),
        name='send_report_link'
    ),
]

youtube_report_views = [
    # Base Report Views
    path(
        'youtube/class/<slug:url_id>',
        youtube_views.YouTubeClassReport.as_view(),
        name='youtube_class_report'
    ),  # slug:url_id relates to Classroom.url_id.
    path(
        'youtube/class/<slug:url_id>/individual/<slug:participant_id>',
        youtube_views.YouTubeIndividualReport.as_view(),
        name='youtube_individual_report'
    ),
    path(
        'youtube/example',
        youtube_views.YouTubeExampleReport.as_view(),
        name='youtube_example_report'
    ),

    # Watch History Section Views
    path(
        'youtube/class/<slug:url_id>/individual/<slug:participant_id>/watch-history-sections',
        youtube_views.WatchHistorySectionsIndividual.as_view(),
        name='youtube_individual_report_wh_sections'
    ),
    path(
        'youtube/class/<slug:url_id>/watch-history-sections',
        youtube_views.WatchHistorySectionsClass.as_view(),
        name='youtube_class_report_wh_sections'
    ),
    path(
        'youtube/example/watch-history-sections',
        youtube_views.WatchHistorySectionsExample.as_view(),
        name='youtube_example_report_wh_sections'
    ),

    # Search History Section Views
    path(
        'youtube/class/<slug:url_id>/individual/<slug:participant_id>/search-history-sections',
        youtube_views.SearchHistorySectionsIndividual.as_view(),
        name='youtube_individual_report_sh_sections'
    ),
    path(
        'youtube/class/<slug:url_id>/search-history-sections',
        youtube_views.SearchHistorySectionsClass.as_view(),
        name='youtube_class_report_sh_sections'
    ),
    path(
        'youtube/example/search-history-sections',
        youtube_views.SearchHistorySectionsExample.as_view(),
        name='youtube_example_report_sh_sections'
    ),

    # Subscription Section Views
    path(
        'youtube/class/<slug:url_id>/subscription-sections',
        youtube_views.SubscriptionSectionsClass.as_view(),
        name='youtube_class_report_sub_sections'
    ),
]

tiktok_report_views = [
    # Base Report Views
    path(
        'tiktok/class/<slug:url_id>',
        tiktok_views.TikTokClassReport.as_view(),
        name='tiktok_class_report'
    ),  # slug:url_id relates to Classroom.url_id.
    path(
        'tiktok/class/<slug:url_id>/individual/<slug:participant_id>',
        tiktok_views.TikTokIndividualReport.as_view(),
        name='tiktok_individual_report'
    ),
    path(
        'tiktok/example',
        tiktok_views.TikTokExampleReport.as_view(),
        name='tiktok_example_report'
    ),

    # Watch History Section Views
    path(
        'tiktok/class/<slug:url_id>/individual/<slug:participant_id>/watch-history-sections',
        tiktok_views.WatchHistorySectionsIndividual.as_view(),
        name='tiktok_individual_report_wh_sections'
    ),
    path(
        'tiktok/class/<slug:url_id>/watch-history-sections',
        tiktok_views.WatchHistorySectionsClass.as_view(),
        name='tiktok_class_report_wh_sections'
    ),
    path(
        'tiktok/example/watch-history-sections',
        tiktok_views.WatchHistorySectionsExample.as_view(),
        name='tiktok_example_report_wh_sections'
    ),

    # Search History Section Views
    path(
        'tiktok/class/<slug:url_id>/individual/<slug:participant_id>/search-history-sections',
        tiktok_views.SearchHistorySectionsIndividual.as_view(),
        name='tiktok_individual_report_sh_sections'
    ),
    path(
        'tiktok/class/<slug:url_id>/search-history-sections',
        tiktok_views.SearchHistorySectionsClass.as_view(),
        name='tiktok_class_report_sh_sections'
    ),
    path(
        'tiktok/example/search-history-sections',
        tiktok_views.SearchHistorySectionsExample.as_view(),
        name='tiktok_example_report_sh_sections'
    ),
]

urlpatterns += youtube_report_views
urlpatterns += tiktok_report_views
