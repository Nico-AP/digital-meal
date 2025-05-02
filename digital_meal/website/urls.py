from django.urls import path, include
from .views import StyleGuide, NewsletterSignupPage


urlpatterns = [
    path('styleguide', StyleGuide.as_view(), name='styleguide'),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('cms/', include('wagtail.admin.urls')),
    path('documents/', include('wagtail.documents.urls')),
    path('newsletter/', NewsletterSignupPage.as_view(), name='newsletter'),
    path('', include('wagtail.urls')),
]
