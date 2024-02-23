from django.urls import path, include

from .views import base as dm_views
from .views import reports as dm_reports
from . import apis as dm_apis


urlpatterns_website = [
    path('styleguide', dm_views.StyleGuide.as_view(), name='styleguide'),
    path('profil/', dm_views.ProfileView.as_view(), name='profile'),
]

urlpatterns_tool = [
    path('', dm_views.ToolMainPage.as_view(), name='tool_main_page'),
    path('class/create', dm_views.ClassroomCreate.as_view(), name='class_create'),
    path('class/<int:pk>/assign-track', dm_views.ClassroomAssignTrack.as_view(), name='class_assign_track'),
    path('class/<int:pk>', dm_views.ClassroomDetail.as_view(), name='class_detail'),
    path('class/<int:pk>/report', dm_reports.ClassroomReportYouTube.as_view(), name='class_report'),
    path('class/<int:pk>/expired', dm_views.ClassroomExpired.as_view(), name='class_expired'),
]

urlpatterns_reports = [
    path('<int:pk>/individual/<slug:participant_id>', dm_reports.IndividualReportYouTube.as_view(),
         name='individual_report'),  # int:pk relates to ID of classroom.
]

urlpatterns_apis = [
    path('<int:pk>/class-data', dm_apis.ClassReportAPI.as_view(), name='class_data_api'),  # int:pk relates to ID of DDM project.  <!-- TODO: Rename int:pk to be more meaningful. -->
    path('<int:pk>/class-overview', dm_apis.ClassOverviewAPI.as_view(), name='class_overview_api'),  # int:pk relates to ID of DDM project.
    path('<int:pk>/individual-data', dm_apis.IndividualReportAPI.as_view(), name='individual_data_api')  # int:pk relates to ID of DDM project.
]

urlpatterns = [
    path('', include(urlpatterns_website)),
    path('reports/', include(urlpatterns_reports)),
    path('tool/', include(urlpatterns_tool)),
    path('api/', include(urlpatterns_apis)),
]
