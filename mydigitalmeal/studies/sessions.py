from dataclasses import dataclass, field, fields
from datetime import datetime

from django.utils import timezone

from mydigitalmeal.studies.constants import STUDIES_SESSION_KEY


@dataclass
class StudyParticipationSession:

    url_parameters: dict = field(default_factory=dict)
    ddm_project_id: str | None = None
    method: str | None = None
    enroll_time: datetime = field(default_factory=timezone.now)

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
