"""Shared constants for the portability app."""

from django.db import models


class PortabilityContexts(models.TextChoices):
    DM_EDU = "DM_EDU", "Digital Meal Education"
    MY_DM = "MY_DM", "My Digital Meal"
