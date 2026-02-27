from enum import Enum

USERFLOW_SESSION_KEY = "mdm_session"


class URLShortcut(str, Enum):
    LANDING = "userflow:landing_page"
    LOGIN = "userflow:profiles:auth"
    CONFIRM_LOGIN = "userflow:profiles:confirm_login_code"
    OVERVIEW = "userflow:overview"
    DONATION_DDM = "userflow:datadonation:datadonation_ddm"
    DONATION_PORTABILITY = "userflow:datadonation:port_tt_connect"
    QUESTIONNAIRE = "userflow:questionnaire:questionnaire"
    REPORT = "userflow:reports:tiktok_report"
