from django.urls import path
from django.views.generic import TemplateView

from digital_meal.views import base as dm_views
from digital_meal.views import reports as dm_reports
from digital_meal import apis as dm_apis


urlpatterns = [
    path('', TemplateView.as_view(template_name='digital_meal/base.html'), name='dm-landing'),
    path('lehrpersonen', TemplateView.as_view(template_name='digital_meal/temp_lehrpersonen.html'), name='dm-lehrpersonen'),  # TODO: Rollback before commit.
    path('class/<int:pk>', dm_views.ClassroomDetail.as_view(), name='classroom-detail'),
    path('class/create', dm_views.ClassroomCreate.as_view(), name='classroom-create'),
    path('class/<int:pk>/assign-track', dm_views.ClassroomAssignTrack.as_view(), name='classroom-assign-track'),
    path('class/<int:pk>/report', dm_reports.ClassroomReportYouTube.as_view(), name='classroom-report'),
    path('class/<int:pk>/expired', dm_views.ClassroomExpired.as_view(), name='classroom-expired'),
    path('report/<int:pk>/individual/<slug:participant_id>', dm_reports.IndividualReportYouTube.as_view(), name='individual-report'),
    path('profil/', dm_views.ProfileView.as_view(), name='profile'),
    path('profil/uebersicht', dm_views.ProfileOverview.as_view(), name='profile-overview'),
    path('styleguide', dm_views.StyleGuide.as_view(), name='styleguide'),
    # APIs
    path('api/<int:pk>/class-data', dm_apis.ClassReportAPI.as_view(), name='class-data-api'),
    path('api/<int:pk>/class-overview', dm_apis.ClassOverviewAPI.as_view(), name='class-overview-api'),
    path('api/<int:pk>/individual-data', dm_apis.IndividualReportAPI.as_view(), name='individual-data-api')
]
