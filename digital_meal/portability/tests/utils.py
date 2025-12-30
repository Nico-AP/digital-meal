from django.contrib.sessions.middleware import SessionMiddleware
from django.core.handlers.wsgi import WSGIRequest
from django.test import RequestFactory


def get_request_with_session(path: str = '/') -> WSGIRequest:
    factory = RequestFactory()
    request = factory.get(path)

    # Add session middleware to the request
    middleware = SessionMiddleware(lambda x: None)
    middleware.process_request(request)
    request.session.save()

    return request
