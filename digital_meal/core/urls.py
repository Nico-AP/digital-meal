from django.urls import include, path

urlpatterns = [
    path("reports/", include("digital_meal.reports.urls")),
    path("tool/", include("digital_meal.tool.urls")),
    path("dashboard/", include("digital_meal.dashboard.urls")),
    path("", include("digital_meal.website.urls")),
]
