from django.urls import path
from django.views.generic import TemplateView

from .views import TikTokAuthView, TikTokCallbackView, TikTokDataReviewView

urlpatterns = [
    path('tiktok/auth/', TikTokAuthView.as_view(), name='tiktok_auth'),
    path('tiktok/auth/callback/', TikTokCallbackView.as_view(), name='tiktok_callback'),
    path('tiktok/review', TikTokDataReviewView.as_view(), name='tiktok_data_review'),
    path('tiktok/review/declined',
         TemplateView.as_view(template_name='portability/tiktok_data_review_declined.html'), name='tiktok_declined'),
]
