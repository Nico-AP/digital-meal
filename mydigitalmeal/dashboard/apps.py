from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mydigitalmeal.dashboard"
    verbose_name = "My Digital Meal Dashboard"
    label = "mydigitalmeal_dashboard"
