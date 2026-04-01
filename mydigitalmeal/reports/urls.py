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
    path(
        "tiktok/report-unavailable/",
        tiktok_views.NoReportView.as_view(),
        name="report_unavailable",
    ),
]


urlpatterns += tiktok_report_views
