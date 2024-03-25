from django.urls import path

from . import views


urlpatterns = [
    path('', views.ToolMainPage.as_view(), name='tool_main_page'),
    path('class/create', views.ClassroomCreate.as_view(), name='class_create'),
    path('class/<int:pk>', views.ClassroomDetail.as_view(), name='class_detail'),
    path('class/<int:pk>/track', views.ClassroomAssignTrack.as_view(), name='class_assign_track'),
    path('class/<int:pk>/expired', views.ClassroomExpired.as_view(), name='class_expired'),
    path('profil/', views.ProfileView.as_view(), name='profile'),
]
