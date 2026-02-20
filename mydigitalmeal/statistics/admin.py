from django.contrib import admin

from mydigitalmeal.statistics.models.base import StatisticsRequest
from mydigitalmeal.statistics.models.tiktok import TikTokWatchHistoryStatistics


@admin.register(TikTokWatchHistoryStatistics)
class TikTokWatchHistoryStatisticsAdmin(admin.ModelAdmin):
    list_display = ["public_id", "scope", "total_videos", "date_created"]
    readonly_fields = ["public_id", "date_created", "date_updated"]
    list_filter = ["scope", "date_created"]


@admin.register(StatisticsRequest)
class StatisticsRequestAdmin(admin.ModelAdmin):
    list_display = ["public_id", "status", "profile", "requested_at", "updated_at"]
    readonly_fields = ["public_id", "requested_at"]
    list_filter = ["status", "requested_at"]
