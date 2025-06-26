from django.urls import path, include


urlpatterns = [
    path('reports/', include('digital_meal.reports.urls')),
    path('tool/', include('digital_meal.tool.urls')),
    path('portability/', include('digital_meal.portability.urls')),
    path('', include('digital_meal.website.urls')),
]
