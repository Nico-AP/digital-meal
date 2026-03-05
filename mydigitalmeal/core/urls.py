from django.urls import include, path

app_name = "mdm"
# IMPORTANT: It is important that this stays fixed;
#  routing between DM and MDM depends on it.

urlpatterns = [
    path(
        "",
        include("mydigitalmeal.userflow.urls", namespace="userflow"),
    ),
    path("", include("mydigitalmeal.infopages.urls", namespace="infopages")),
]
