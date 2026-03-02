import logging
import time
from collections import defaultdict


class ThrottledAdminEmailFilter(logging.Filter):
    """Throttle admin error emails to prevent inbox flooding.

    Groups errors by signature (exception type + module + function).
    Allows max 1 email per signature per throttle_seconds window.
    When an email is sent after suppression, includes a count of
    how many similar errors were suppressed.
    """

    def __init__(self, throttle_seconds=600):
        super().__init__()
        self.throttle_seconds = throttle_seconds
        self._timestamps: dict[str, float] = {}
        self._suppressed_counts: dict[str, int] = defaultdict(int)

    def _get_signature(self, record):
        exc_type = "NoException"
        if record.exc_info and record.exc_info[0]:
            exc_type = record.exc_info[0].__name__
        return f"{exc_type}:{record.module}:{record.funcName}"

    def filter(self, record):
        signature = self._get_signature(record)
        now = time.monotonic()
        last_sent = self._timestamps.get(signature, 0)

        if now - last_sent < self.throttle_seconds:
            self._suppressed_counts[signature] += 1
            return False

        suppressed = self._suppressed_counts.pop(signature, 0)
        if suppressed > 0:
            record.msg = (
                f"[{suppressed} similar error(s) suppressed in the last "
                f"{self.throttle_seconds}s]\n{record.msg}"
            )
            record.args = ()

        self._timestamps[signature] = now
        return True
