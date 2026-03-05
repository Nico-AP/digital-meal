from django.apps import AppConfig


class SharedRoutingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shared.routing"
    label = "routing"
    verbose_name = "Digital Meal Routing"
