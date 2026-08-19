from enum import StrEnum

STUDIES_SESSION_KEY = "mdm_studies_session"
SECONDS_TO_REMINDER = 3 * 60  # test value: 10

TRAIL_KEY = "participation_trail"


class DLULTrailSteps(StrEnum):
    ENROLLED = "enrolled"  # Keep in sync with PAPITrailSteps.ENROLLED
    INSTRUCTIONS = "dlul-2_entered_instructions"
    GOT_REMINDER = "dlul-3_got_reminder_info"
    QUESTIONNAIRE = "dlul-4_entered_questionnaire"
    DEBRIEF = "dlul-5_entered_debrief"


def get_dlul_trail() -> dict[str, list]:
    return {k: [] for k in DLULTrailSteps}


class PAPITrailSteps(StrEnum):
    ENROLLED = "enrolled"  # Keep in sync with DLULTrailSteps.ENROLLED
    WAITING_VIEW = "papi-2_entered_waiting_view"
    ERROR_VIEW = "papi-2_entered_error_view"
    ABORT_VIEW = "papi-2_entered_abort_view"
    WAITING_SUCCESS = "papi-3_got_waiting_success"
    WAITING_ERROR = "papi-3_got_waiting_error"
    WAITING_REMINDER = "papi-3_got_waiting_reminder"
    UPLOAD = "papi-4_entered_upload"
    QUESTIONNAIRE = "papi-5_entered_questionnaire"
    DEBRIEF = "papi-6_entered_debrief"


def get_papi_trail() -> dict[str, list]:
    return {k: [] for k in PAPITrailSteps}


class StudiesURLShortcut(StrEnum):
    ENROLL = "mdm:userflow:studies:enroll"
    DONATION_DDM = "mdm:userflow:studies:download_upload"
    DONATION_PORTABILITY = "mdm:userflow:studies:port_tt_connect"
    QUESTIONNAIRE = "mdm:userflow:studies:questionnaire"
    DEBRIEFING = "mdm:userflow:studies:debriefing"
    REPORT = "mdm:userflow:studies:report"
    REPORT_UNAVAILABLE = "mdm:userflow:reports:report_unavailable"
