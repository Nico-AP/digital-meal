from django.urls import path, include

from .views import base as dm_views
from .views import reports as dm_reports


urlpatterns_tool = [
    path('', dm_views.ToolMainPage.as_view(), name='tool_main_page'),
    path('class/create', dm_views.ClassroomCreate.as_view(), name='class_create'),
    path('class/<int:pk>/assign-track', dm_views.ClassroomAssignTrack.as_view(), name='class_assign_track'),
    path('class/<int:pk>', dm_views.ClassroomDetail.as_view(), name='class_detail'),
    path('class/<int:pk>/report', dm_reports.ClassroomReportYouTube.as_view(), name='class_report'),
    path('class/<int:pk>/expired', dm_views.ClassroomExpired.as_view(), name='class_expired'),
    path('profil/', dm_views.ProfileView.as_view(), name='profile'),
]

urlpatterns_reports = [
    path('<int:pk>/individual/<slug:participant_id>', dm_reports.IndividualReportYouTube.as_view(),
         name='individual_report'),  # int:pk relates to ID of classroom.
    path('send-report-link', dm_reports.SendReportLink.as_view(), name='send_report_link')
]

urlpatterns = [
    path('reports/', include(urlpatterns_reports)),
    path('tool/', include(urlpatterns_tool))
]
