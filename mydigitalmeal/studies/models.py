from django.db import models
from django_ckeditor_5.fields import CKEditor5Field


class StudyProject(models.Model):
    project = models.OneToOneField(
        "ddm_projects.DonationProject",
        on_delete=models.CASCADE,
        related_name="study_project",
    )
    show_reminder = models.BooleanField(default=False)
    show_report_invite_link = models.BooleanField(default=False)
    report_invite_link = models.URLField(blank=True)

    portability_briefing = CKEditor5Field(
        "Porability Briefing Text",
        config_name="ddm_ckeditor",
        blank=True,
    )

    def __str__(self):
        return f"Study project for {self.project.name}"
