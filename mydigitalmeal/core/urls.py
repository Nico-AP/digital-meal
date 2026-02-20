from django.urls import include, path

urlpatterns = [
    path(
        "",
        include("mydigitalmeal.userflow.urls", namespace="userflow"),
    ),
]
