from django.urls import path

from digital_meal.dashboard.views import DashboardView, ParticipantStatsView

urlpatterns = [
    path(
        '',
        DashboardView.as_view(),
        name='dashboard'
    ),
    path(
        'participant-stats',
        ParticipantStatsView.as_view(),
        name='dashboard_participant_stats'
    ),
]