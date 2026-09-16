from django.contrib import admin

from mydigitalmeal.studies.models import StudyProject


@admin.register(StudyProject)
class StudyProjectAdmin(admin.ModelAdmin):
    list_display = [
        "project",
        "show_reminder",
        "show_report_invite_link",
        "report_invite_link",
    ]
