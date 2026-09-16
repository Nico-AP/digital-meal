from django.db import models


class StudyProject(models.Model):
    project = models.OneToOneField(
        "ddm_projects.DonationProject",
        on_delete=models.CASCADE,
        related_name="study_project",
    )
    show_reminder = models.BooleanField(default=False)
    show_report_invite_link = models.BooleanField(default=False)
    report_invite_link = models.URLField()

    def __str__(self):
        return f"Study project for {self.project.name}"
