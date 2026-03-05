from contextvars import ContextVar

current_request_var = ContextVar("current_request", default=None)
