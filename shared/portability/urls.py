from django.urls import path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path(
        'tiktok/auth/',
        views.TikTokAuthView.as_view(),
        name='tiktok_auth'
    ),
    path(
        'tiktok/auth/callback/',
        views.TikTokCallbackView.as_view(),
        name='tiktok_callback'
    ),
    path(
        'tiktok/await-data',
        views.TikTokAwaitDataDownloadView.as_view(),
        name='tiktok_await_data_download'
    ),
    path(
        'tiktok/check-status',
        views.TikTokCheckDownloadAvailabilityView.as_view(),
        name='tiktok_check_download_availability'
    ),
    path(
        'tiktok/download-data/<int:request_id>',
        views.TikTokDataDownloadView.as_view(),
        name='tiktok_download_data'
    ),
    path(
        'tiktok/review',
        views.TikTokDataReviewView.as_view(),
        name='tiktok_data_review'
    ),
    path(
        'tiktok/review/declined',
         TemplateView.as_view(template_name='portability/tiktok_data_review_declined.html'),
        name='tiktok_declined'
    ),
    path(
        'tiktok/disconnect',
        views.TikTokDisconnectView.as_view(),
        name='tiktok_disconnect'
    ),
]
