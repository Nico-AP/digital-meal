from django.urls import path, include
from .views import StyleGuide


urlpatterns = [
    path('styleguide', StyleGuide.as_view(), name='styleguide'),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('cms/', include('wagtail.admin.urls')),
    path('documents/', include('wagtail.documents.urls')),
    path('', include('wagtail.urls')),
]
