import uuid

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class MDMProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="mdm_profile",
    )

    public_id = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When first login for profile was registered.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "My Digital Meal Profile"
        verbose_name_plural = "My Digital Meal Profiles"

    def __str__(self):
        return f"MDM Profile {self.public_id}"

    def get_absolute_url(self) -> str:
        """Get URL for user's profile detail view."""
        return reverse(
            "profiles:detail",
            kwargs={"public_id": self.public_id},
        )  # TODO: Adjust in urls.py

    def activate(self):
        if not self.activated_at:
            self.activated_at = timezone.now()
            self.save(update_fields=["activated_at"])
