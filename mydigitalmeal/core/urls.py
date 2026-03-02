from django.urls import include, path

urlpatterns = [
    path(
        "",
        include("mydigitalmeal.userflow.urls", namespace="userflow"),
    ),
    path("", include("mydigitalmeal.infopages.urls", namespace="infopages")),
]
