from enum import StrEnum

_MDM_URLCONF = "config.urls.mdm_conf"
_MAIN_URLCONF = "config.urls.main_conf"


class MDMRoutingModes(StrEnum):
    URL_PREFIX = "URL_PREFIX"
    SUBDOMAIN = "SUBDOMAIN"


class MDMRoutingContext(StrEnum):
    MY_DM = "My Digital Meal"
    DM_MAIN = "Digital Meal Main"
