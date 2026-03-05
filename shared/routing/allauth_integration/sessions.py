from dataclasses import dataclass

from shared.routing.allauth_integration.settings import AUTH_SESSION_KEY, AuthContexts


@dataclass
class AuthSession:
    auth_context: AuthContexts | None = None

    def __post_init__(self):
        if isinstance(self.auth_context, str):
            self.auth_context = AuthContexts(self.auth_context)

    def to_session_dict(self) -> dict:
        """Serialize to a JSON-safe dict, converting enums to their values."""
        return {
            "auth_context": self.auth_context.value if self.auth_context else None,
        }


class AuthSessionManager:
    SESSION_KEY = AUTH_SESSION_KEY

    def __init__(self, session):
        self._request_session = session

    @classmethod
    def from_request(cls, request):
        return cls(session=request.session)

    def initialize(self) -> AuthSession:
        if self.SESSION_KEY not in self._request_session:
            auth_session = AuthSession()
            self._request_session[self.SESSION_KEY] = auth_session.to_session_dict()
        else:
            auth_session = self.get()
        return auth_session

    def get(self) -> AuthSession | None:
        session_data = self._request_session.get(self.SESSION_KEY)
        return AuthSession(**session_data) if session_data else None

    def get_auth_context(self) -> AuthContexts | None:
        session_data = self.get()
        return session_data.auth_context if session_data else None

    def update(self, **updates) -> AuthSession:
        auth_session = self.get() or self.initialize()
        for key, value in updates.items():
            setattr(auth_session, key, value)

        self._request_session[self.SESSION_KEY] = auth_session.to_session_dict()
        self._request_session.modified = True
        return auth_session

    def reset(self) -> AuthSession:
        auth_session = AuthSession()
        self._request_session[self.SESSION_KEY] = auth_session.to_session_dict()
        return auth_session

    def delete(self) -> None:
        self._request_session.pop(self.SESSION_KEY, None)
