from django.views.generic import TemplateView


class AboutView(TemplateView):
    template_name = "infopages/pages/about.html"


class BackgroundView(TemplateView):
    template_name = "infopages/pages/background.html"


class DataProtectionView(TemplateView):
    template_name = "infopages/pages/data_protection.html"


class TermsOfServiceView(TemplateView):
    template_name = "infopages/pages/tos.html"


class DataProtectionStatementView(TemplateView):
    template_name = "infopages/pages/dps.html"
