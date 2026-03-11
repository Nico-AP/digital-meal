from django.urls import path

import mydigitalmeal.reports.views.tiktok as tiktok_views

app_name = "reports"
urlpatterns = []

tiktok_report_views = [
    path(
        "tiktok/",
        tiktok_views.MainReportView.as_view(),
        name="tiktok_report",
    ),
    path(
        "tiktok/partials/statistics/",
        tiktok_views.StatisticsView.as_view(),
        name="tiktok_statistics",
    ),
]


urlpatterns += tiktok_report_views
