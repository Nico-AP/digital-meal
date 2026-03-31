from dataclasses import asdict, dataclass, replace

from shared.portability.constants import PortabilityContexts


@dataclass
class PortabilitySession:
    context: PortabilityContexts | None = None
    state_token: str | None = None
    tiktok_open_id: str | None = None

    def __post_init__(self):
        if isinstance(self.context, str):
            self.context = PortabilityContexts(self.context)


PORTABILITY_SESSION_KEY = "portability"


class PortabilitySessionManager:
    SESSION_KEY = PORTABILITY_SESSION_KEY

    def __init__(self, session):
        self._request_session = session

    @classmethod
    def from_request(cls, request):
        return cls(session=request.session)

    def initialize(self) -> PortabilitySession:
        if self.SESSION_KEY not in self._request_session:
            portability_session = PortabilitySession()
            self._request_session[self.SESSION_KEY] = asdict(portability_session)
        else:
            portability_session = self.get()
        return portability_session

    def get(self) -> PortabilitySession | None:
        session_data = self._request_session.get(self.SESSION_KEY)
        return PortabilitySession(**session_data) if session_data else None

    def get_token(self) -> str | None:
        session_data = self.get()
        return session_data.state_token if session_data else None

    def get_context(self) -> PortabilityContexts | None:
        session_data = self.get()
        return session_data.context if session_data else None

    def get_tiktok_open_id(self) -> str | None:
        session_data = self.get()
        return session_data.tiktok_open_id if session_data else None

    def update(self, **updates) -> PortabilitySession:
        portability_session = self.get() or PortabilitySession()
        portability_session = replace(portability_session, **updates)

        self._request_session[self.SESSION_KEY] = asdict(portability_session)
        self._request_session.modified = True
        return portability_session

    def reset(self) -> PortabilitySession:
        portability_session = PortabilitySession()
        self._request_session[self.SESSION_KEY] = asdict(portability_session)
        return portability_session

    def delete(self) -> None:
        self._request_session.pop(self.SESSION_KEY, None)

    def delete_token(self) -> PortabilitySession:
        return self.update(state_token=None)

    def delete_tiktok_open_id(self) -> PortabilitySession:
        return self.update(tiktok_open_id=None)


class PortabilitySessionMixin:
    """Initialises the portability session and provides a session-dispatch hook.

    Subclasses and cooperative mixins should override `session_dispatch()` rather
    than `dispatch()` to perform request validation. This guarantees that
    `self.port_session` is always initialised before any session-related
    validation logic runs.

    Must be listed after any mixin that accesses `self.port_session` in a
    view's inheritance chain.
    """

    port_session: PortabilitySessionManager | None = None

    def dispatch(self, request, *args, **kwargs):
        """Initialises self.port_session, then delegates to session_dispatch()."""
        self.port_session = PortabilitySessionManager.from_request(request)
        response = self.session_dispatch(request, *args, **kwargs)
        if response:
            return response
        return super().dispatch(request, *args, **kwargs)

    def session_dispatch(self, request, *args, **kwargs) -> None:
        """Terminal of the session_dispatch chain.

        Called after self.port_session is set.

        Override in subclasses to perform validation before the request is routed
        to a handler. Cooperative mixins must call `super().session_dispatch()` to
        allow the full chain to run.

        Returns:
          None to allow the request to proceed, or an HttpResponse to
          short-circuit dispatch and return immediately.
        """
        return None
