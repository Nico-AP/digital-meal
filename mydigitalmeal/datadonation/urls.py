from django.urls import path

import mydigitalmeal.datadonation.views.ddm as ddm_views
import mydigitalmeal.datadonation.views.portability as port_views

app_name = "datadonation"
urlpatterns = [
    path(
        "get-data/",
        ddm_views.DonationViewDDM.as_view(),
        name="datadonation_ddm",
    ),
    path(
        "connect/",
        port_views.PortabilityEntryView.as_view(),
        name="port_tt_connect",
    ),
]
