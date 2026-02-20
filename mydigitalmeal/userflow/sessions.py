from dataclasses import dataclass
from uuid import UUID

from mydigitalmeal.userflow.constants import USERFLOW_SESSION_KEY


@dataclass
class UserflowSession:
    statistics_requested: bool = False
    # Can be False, when donation/data upload step was skipped.

    request_id: UUID | None = None

    def to_dict(self) -> dict:
        return {
            "statistics_requested": self.statistics_requested,
            "request_id": str(self.request_id) if self.request_id else None,
        }


class UserflowSessionManager:
    SESSION_KEY = USERFLOW_SESSION_KEY

    def __init__(self, session):
        self._request_session = session

    @classmethod
    def from_request(cls, request):
        return cls(session=request.session)

    def initialize(self) -> UserflowSession:
        if self.SESSION_KEY not in self._request_session:
            userflow_session = UserflowSession()
            self._request_session[self.SESSION_KEY] = userflow_session.to_dict()
        else:
            userflow_session = self.get()
        return userflow_session

    def get(self) -> UserflowSession | None:
        session_data = self._request_session.get(self.SESSION_KEY)
        if session_data:
            return UserflowSession(**session_data)
        return None

    def update(self, **updates) -> UserflowSession:
        userflow_session = self.get()
        if not userflow_session:
            userflow_session = self.initialize()
        for key, value in updates.items():
            setattr(userflow_session, key, value)

        self._request_session[self.SESSION_KEY] = userflow_session.to_dict()
        self._request_session.modified = True
        return userflow_session

    def reset(self) -> UserflowSession:
        userflow_session = UserflowSession()
        self._request_session[self.SESSION_KEY] = userflow_session.to_dict()
        return userflow_session

    def delete(self) -> None:
        self._request_session.pop(self.SESSION_KEY, None)


class AddUserflowSessionMixin:
    userflow_session: UserflowSessionManager | None = None

    def dispatch(self, request, *args, **kwargs):
        self.userflow_session = UserflowSessionManager.from_request(request)
        validation_response = self.validate_userflow_session(request, *args, **kwargs)
        if validation_response:
            return validation_response
        return super().dispatch(request, *args, **kwargs)

    def validate_userflow_session(self, request, *args, **kwargs):
        """Override this method for view-based userflow session validation"""
        return
