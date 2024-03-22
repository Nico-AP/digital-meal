from django.urls import path

from . import apis as dm_apis


urlpatterns = [
    path('<int:pk>/class-data', dm_apis.ClassReportAPI.as_view(), name='class_data_api'),  # int:pk relates to ID of DDM project (must be named 'pk' due to ddm authentication scheme).
    path('<int:pk>/class-overview', dm_apis.ClassOverviewAPI.as_view(), name='class_overview_api'),  # int:pk relates to ID of DDM project.
    path('<int:pk>/individual-data', dm_apis.IndividualReportAPI.as_view(), name='individual_data_api')  # int:pk relates to ID of DDM project.
]
