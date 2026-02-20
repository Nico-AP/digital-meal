from django.urls import path

from mydigitalmeal.questionnaire import views

app_name = "questionnaire"
urlpatterns = [
    path(
        "questionnaire/",
        views.MDMQuestionnaireView.as_view(),
        name="questionnaire",
    ),
]
