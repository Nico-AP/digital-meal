from django.urls import path

from . import apis


urlpatterns = [
    path(
        '<int:pk>/class-data',  # int:pk relates to ID of DDM project (must be named 'pk' due to ddm authentication scheme).
        apis.ClassReportAPI.as_view(),
        name='class_data_api'
    ),
    path(
        '<int:pk>/class-overview',  # int:pk relates to ID of DDM project.
        apis.ClassOverviewAPI.as_view(),
        name='class_overview_api'
    ),
    path(
        '<int:pk>/individual-data',  # int:pk relates to ID of DDM project.
        apis.IndividualReportAPI.as_view(),
        name='individual_data_api'
    )
]
