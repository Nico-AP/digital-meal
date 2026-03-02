from django.urls import path

from mydigitalmeal.infopages import views

app_name = "infopages"
urlpatterns = [
    path("about/", views.AboutView.as_view(), name="about"),
    path("info/", views.BackgroundView.as_view(), name="background"),
    path("dataprotection/", views.DataProtectionView.as_view(), name="data_protection"),
    path("tos/", views.TermsOfServiceView.as_view(), name="tos"),
    path("dps/", views.DataProtectionStatementView.as_view(), name="dps"),
]
