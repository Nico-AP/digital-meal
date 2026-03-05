from enum import StrEnum

USERFLOW_SESSION_KEY = "mdm_session"


class URLShortcut(StrEnum):
    LANDING = "mdm:userflow:landing_page"
    LOGIN = "mdm:userflow:profiles:auth"
    CONFIRM_LOGIN = "mdm:userflow:profiles:confirm_login_code"
    OVERVIEW = "mdm:userflow:overview"
    DONATION_DDM = "mdm:userflow:datadonation:datadonation_ddm"
    DONATION_PORTABILITY = "mdm:userflow:datadonation:port_tt_connect"
    QUESTIONNAIRE = "mdm:userflow:questionnaire:questionnaire"
    REPORT = "mdm:userflow:reports:tiktok_report"
