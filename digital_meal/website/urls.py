from django.urls import path, include
from django.views.generic import TemplateView
from wagtail.contrib.sitemaps.views import sitemap

from .views import StyleGuide, NewsletterSignupPage


urlpatterns = [
    path('styleguide', StyleGuide.as_view(), name='styleguide'),
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    path('cms/', include('wagtail.admin.urls')),
    path('documents/', include('wagtail.documents.urls')),
    path('newsletter/', NewsletterSignupPage.as_view(), name='newsletter'),
    path('robots.txt', TemplateView.as_view(template_name='website/robots.txt', content_type='text/plain')),
    path('sitemap.xml', sitemap),
    path(
        'google2b303e6246e0b3a0.html',
        TemplateView.as_view(template_name='website/google_search_console_verification.html'),
        name='google_sc_verification'
    ),
    path(
        'tiktokYbzF9wdz4BV0HO6cnUyVPchkKCRyEggr.txt',
        TemplateView.as_view(template_name='website/tiktokYbzF9wdz4BV0HO6cnUyVPchkKCRyEggr.txt'),
        name='tiktok_dev_verification'
    ),
    path('', include('wagtail.urls')),
]
