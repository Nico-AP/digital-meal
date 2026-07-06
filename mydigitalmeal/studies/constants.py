from enum import StrEnum

STUDIES_SESSION_KEY = "mdm_studies_session"
SECONDS_TO_REMINDER = 3 * 60  # test value: 10

PARTICIPATION_TRAIL_DLUL = {
    "a_enrolled": None,
    "b_entered_instructions": None,
    "c_got_reminder_info": None,
    "e_entered_debrief": None,
}

PARTICIPATION_TRAIL_PAPI = {
    "a_enrolled": None,
    "b1_entered_waiting_view": None,
    "b2_entered_error_view": None,
    "b3_entered_abort_view": None,
    "c1_got_waiting_success": None,
    "c2_got_waiting_error": None,
    "c3_got_waiting_reminder_info": None,
    "d1_entered_upload": None,
    "e_entered_debrief": None,
}


class StudiesURLShortcut(StrEnum):
    ENROLL = "mdm:userflow:studies:enroll"
    DONATION_DDM = "mdm:userflow:studies:download_upload"
    DONATION_PORTABILITY = "mdm:userflow:studies:port_tt_connect"
    QUESTIONNAIRE = "mdm:userflow:studies:questionnaire"
    DEBRIEFING = "mdm:userflow:studies:debriefing"
    REPORT = "mdm:userflow:studies:report"
    REPORT_UNAVAILABLE = "mdm:userflow:reports:report_unavailable"
