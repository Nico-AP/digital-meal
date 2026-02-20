from django.contrib import admin

from mydigitalmeal.profiles.models import MDMProfile


@admin.register(MDMProfile)
class MDMProfileAdmin(admin.ModelAdmin):
    list_display = ["public_id"]
