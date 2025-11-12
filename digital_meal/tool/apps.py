from django.apps import AppConfig


class DigitalMealConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'digital_meal.tool'
    verbose_name = 'Digital Meal Tool'

    def ready(self):
        import digital_meal.tool.signals
