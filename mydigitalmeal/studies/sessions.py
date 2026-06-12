from dataclasses import dataclass, field, fields
from datetime import datetime

from mydigitalmeal.studies.constants import STUDIES_SESSION_KEY


@dataclass
class StudyParticipationSession:
    """State recorded when an external survey hands a participant over.

    Persisted into ``request.session`` under
    `mydigitalmeal.studies.constants.STUDIES_SESSION_KEY` and
    consumed throughout the studies flow as the sole authentication
    signal (study participants never log in). Presence of
    ``ddm_project_id`` is what ``RequireStudySessionMixin`` treats as
    "enrolment complete" — an empty instance produced by ``reset()`` is
    *not* sufficient.

    Fields:
        url_parameters: Sanitised query-string parameters from the
            enrolment URL (see ``_sanitize_url_parameters`` in
            ``views.py`` for the allowlist and size caps). Replayed onto
            the DDM ``Participant.extra_data`` so survey responses can
            be linked to the donation.
        ddm_project_id: ``DonationProject.url_id`` the participant is
            pinned to at enrolment time. Used by every downstream view
            to resolve the project from the session rather than from a
            URL slug.
        method: One of :class:`DonationMethod` values. Selects the
            portability-API vs. download/upload donation path.
        enroll_time: Stamped by ``StudyEnrollView`` on a successful
            enrolment. Defaults to ``None`` so that round-tripping a
            session dict that omits the key doesn't silently fabricate
            a "now" timestamp.
        completed: Set by ``StudyDebriefingView`` after the participant
            has rendered the debriefing page. Routers consult this to
            decide whether subsequent OAuth-callback / auth-retry
            traffic should still be considered part of an active study
            flow; once True, the browser falls through to the regular
            MDM path.
    """

    url_parameters: dict = field(default_factory=dict)
    ddm_project_id: str | None = None
    method: str | None = None
    enroll_time: datetime | None = None
    completed: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "StudyParticipationSession":
        data = data.copy()
        if isinstance(data.get("enroll_time"), str):
            data["enroll_time"] = datetime.fromisoformat(data["enroll_time"])

        accepted_fields = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in accepted_fields})

    def to_dict(self) -> dict:
        return {
            "url_parameters": self.url_parameters,
            "ddm_project_id": self.ddm_project_id,
            "method": self.method,
            "enroll_time": self.enroll_time.isoformat() if self.enroll_time else None,
            "completed": self.completed,
        }


class StudyParticipationSessionManager:
    SESSION_KEY = STUDIES_SESSION_KEY

    def __init__(self, session):
        self._request_session = session

    @classmethod
    def from_request(cls, request):
        return cls(session=request.session)

    def initialize(self) -> StudyParticipationSession:
        if self.SESSION_KEY not in self._request_session:
            study_session = StudyParticipationSession()
            self._request_session[self.SESSION_KEY] = study_session.to_dict()
            self._request_session.modified = True
        else:
            study_session = self.get()
        return study_session

    def get(self) -> StudyParticipationSession | None:
        session_data = self._request_session.get(self.SESSION_KEY)
        if session_data:
            return StudyParticipationSession.from_dict(session_data)
        return None

    def update(self, **updates) -> StudyParticipationSession:
        study_session = self.initialize()
        for key, value in updates.items():
            setattr(study_session, key, value)

        self._request_session[self.SESSION_KEY] = study_session.to_dict()
        self._request_session.modified = True
        return study_session

    def reset(self) -> StudyParticipationSession:
        study_session = StudyParticipationSession()
        self._request_session[self.SESSION_KEY] = study_session.to_dict()
        self._request_session.modified = True
        return study_session

    def delete(self) -> None:
        self._request_session.pop(self.SESSION_KEY, None)
