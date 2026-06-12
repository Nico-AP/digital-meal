from enum import StrEnum

STUDIES_SESSION_KEY = "mdm_studies_session"


class StudiesURLShortcut(StrEnum):
    ENROLL = "mdm:userflow:studies:enroll"
    DONATION_DDM = "mdm:userflow:studies:download_upload"
    DONATION_PORTABILITY = "mdm:userflow:studies:port_tt_connect"
    QUESTIONNAIRE = "mdm:userflow:studies:questionnaire"
    DEBRIEFING = "mdm:userflow:studies:debriefing"
    REPORT = "mdm:userflow:studies:report"
    REPORT_UNAVAILABLE = "mdm:userflow:reports:report_unavailable"
