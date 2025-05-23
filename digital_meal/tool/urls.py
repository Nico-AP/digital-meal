from django.urls import path, include

from . import views


urlpatterns = [
    path(
        '',
        views.ToolMainPage.as_view(),
        name='tool_main_page'
    ),
    path(
        'class/create',
        views.ClassroomCreate.as_view(),
        name='class_create'
    ),
    path(
        'class/<slug:url_id>',
        views.ClassroomDetail.as_view(),
        name='class_detail'
    ),
    path(
        'class/<slug:url_id>/module',
        views.ClassroomAssignModule.as_view(),
        name='class_assign_module'
    ),
    path(
        'class/<slug:url_id>/expired',
        views.ClassroomExpired.as_view(),
        name='class_expired'
    ),
    path(
        'class/not_found',
        views.ClassroomDoesNotExist.as_view(),
        name='class_not_found'
    ),
    path(
        'profil/',
        views.ProfileView.as_view(),
        name='profile'
    ),
    path(
        'qr_code/',
        include('qr_code.urls', namespace='qr_code')
    ),
]
