from django.urls import path

from mydigitalmeal.profiles import views

app_name = "profiles"
urlpatterns = [
    path(
        "login/",
        views.MDMAuthView.as_view(),
        name="auth",
    ),
    path(
        "login/confirm/",
        views.MDMConfirmLoginCodeView.as_view(),
        name="confirm_login_code",
    ),
    path(
        "logout/confirm/",
        views.MDMLogoutView.as_view(),
        name="logout",
    ),
]
