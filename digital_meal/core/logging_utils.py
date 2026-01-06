import logging
import json
from collections import OrderedDict

from django.http import HttpRequest


ALLOWED_LOGGING_LEVELS = [
    logging.WARNING,
    logging.INFO,
    logging.ERROR,
    logging.CRITICAL
]


class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_data = OrderedDict()

        # Define the order of the first keys
        log_data['timestamp'] = self.formatTime(record)
        log_data['level'] = record.levelname
        log_data['message'] = record.getMessage()

        # Add other standard fields
        log_data['logger'] = record.name
        log_data['line'] = record.lineno

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'created', 'filename', 'funcName',
                           'levelname', 'levelno', 'lineno', 'module', 'msecs',
                           'message', 'pathname', 'process', 'processName',
                           'relativeCreated', 'thread', 'threadName', 'exc_info',
                           'exc_text', 'stack_info', 'asctime']:
                log_data[key] = value

        return json.dumps(log_data)


def log_security_event(
        logger: logging.Logger,
        msg: str,
        request: HttpRequest,
        extra: dict = None,
        level: int = logging.WARNING,
):
    if level not in ALLOWED_LOGGING_LEVELS:
        level = logging.WARNING

    session = getattr(request, 'session', None)

    security_extra = {
        'ip': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT'),
        'session_key': getattr(session, 'session_key', None),
        **(extra or {})
    }

    logger.log(level, msg, extra=security_extra)


def log_requests_exception(
        logger: logging.Logger,
        url: str | None,
        e: Exception,
        msg: str,
        *args,
        extra: dict = None,
        level: int = logging.WARNING,
):
    if level not in ALLOWED_LOGGING_LEVELS:
        level = logging.WARNING

    response = getattr(e, 'response', None)

    try:
        response_text = response.text[:500] if hasattr(response, 'text') else 'no response text available'
    except (AttributeError, TypeError):
        response_text = 'no response text available'

    requests_extra = {
        'status_code': getattr(response, 'status_code', None),
        'response_text': response_text,
        'error_type': type(e).__name__,
        'url': url,
        **(extra or {})
    }

    logger.log(level, msg, *args, extra=requests_extra)
