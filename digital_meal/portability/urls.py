from django.urls import path
from .views import TikTokAuthView, TikTokCallbackView, TikTokDataReviewView

urlpatterns = [
    path('tiktok/auth/', TikTokAuthView.as_view(), name='tiktok_auth'),
    path('tiktok/auth/callback/', TikTokCallbackView.as_view(), name='tiktok_callback'),
    path('tiktok/review', TikTokDataReviewView.as_view(), name='tiktok_data_review'),
]
