from enum import StrEnum

from django.conf import settings

TIKTOK_PROJECT_SLUG = settings.MDM_DDM_TIKTOK_PROJECT_SLUG
TIKTOK_WATCH_HISTORY_BP_NAME = settings.MDM_DDM_TIKTOK_WH_BP_NAME

class DonationMethod(StrEnum):
    PORTABILITY = "port-api"
    DOWNLOAD_UPLOAD = "download-upload"
