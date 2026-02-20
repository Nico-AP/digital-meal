from django.urls import path

import mydigitalmeal.datadonation.views.ddm as ddm_views

app_name = "datadonation"
urlpatterns = [
    path(
        "donation-ddm/",
        ddm_views.DonationViewDDM.as_view(),
        name="datadonation_ddm",
    ),
]
