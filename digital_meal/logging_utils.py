import logging
import json
from collections import OrderedDict

from django.http import HttpRequest


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
    allowed_levels = [
        logging.WARNING,
        logging.INFO,
        logging.ERROR,
        logging.CRITICAL
    ]

    if level not in allowed_levels:
        level = logging.WARNING

    security_extra = {
        'ip': request.META.get('REMOTE_ADDR'),
        'user_agent': request.META.get('HTTP_USER_AGENT'),
        'session_key': getattr(request.session, 'session_key', None),
        **(extra or {})
    }

    logger.log(level, msg, extra=security_extra)
