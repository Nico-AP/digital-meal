from django.urls import path

import digital_meal.dashboard.views as views

urlpatterns = [
    path(
        '',
        views.DashboardView.as_view(),
        name='dashboard'
    ),
    path(
        'classroom-overview',
        views.ClassroomOverviewView.as_view(),
        name='dashboard_classroom_overview'
    ),
    path(
        'teacher-overview',
        views.TeacherOverviewView.as_view(),
        name='dashboard_teacher_overview'
    ),
    path(
        'participation-overview',
        views.ParticipationOverviewView.as_view(),
        name='dashboard_participation_overview'
    ),
    path(
        'exception-overview',
        views.ExceptionOverviewView.as_view(),
        name='dashboard_exception_overview'
    ),
]
