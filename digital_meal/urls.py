from django.urls import path
from django.views.generic import TemplateView

from digital_meal import views as dm_views


urlpatterns = [
    path('', TemplateView.as_view(template_name='digital_meal/base.html'), name='dm-landing'),
    path('lehrpersonen', TemplateView.as_view(template_name='digital_meal/temp_lehrpersonen.html'), name='dm-lehrpersonen'),  # TODO: Rollback before commit.
    path('class/<int:pk>', dm_views.ClassroomDetail.as_view(), name='classroom-detail'),
    path('class/create', dm_views.ClassroomCreate.as_view(), name='classroom-create'),
    path('class/list', dm_views.ClassroomList.as_view(), name='classroom-list'),
    path('report/<slug:external_pool_project_id>/<slug:external_pool_participant_id>', dm_views.IndividualReport.as_view(), name='individual-report'),
    path('report/pdf/<slug:external_pool_project_id>/<slug:external_pool_participant_id>', dm_views.IndividualReportPDF.as_view(), name='individual-report-as-pdf'),
    path('profil/', dm_views.ProfileView.as_view(), name='profile'),
    path('styleguide', dm_views.StyleGuide.as_view(), name='styleguide')
]
