import uuid

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, TestCase

from mydigitalmeal.userflow.constants import USERFLOW_SESSION_KEY
from mydigitalmeal.userflow.sessions import UserflowSessionManager


class TestUserflowSessionManager(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")
        session_middleware = SessionMiddleware(get_response=lambda r: None)
        session_middleware.process_request(self.request)
        self.request.session.save()

    def test_from_request(self):
        manager = UserflowSessionManager.from_request(self.request)
        self.assertIsNotNone(manager._request_session)
        self.assertEqual(manager._request_session, self.request.session)

    def test_init(self):
        session = {"something": 123}
        manager = UserflowSessionManager(session)
        self.assertIsNotNone(manager._request_session)

        empty_session = {}
        manager = UserflowSessionManager(empty_session)
        self.assertIsNotNone(manager._request_session)

    def test_initialization_no_session(self):
        manager = UserflowSessionManager.from_request(self.request)
        manager.initialize()
        self.assertIn(USERFLOW_SESSION_KEY, self.request.session)

    def test_initialization_with_existing_session(self):
        self.request.session[USERFLOW_SESSION_KEY] = {
            "statistics_requested": True,
            "request_id": None,
        }

        manager = UserflowSessionManager.from_request(self.request)
        state = manager.initialize()

        self.assertEqual(state.statistics_requested, True)
        self.assertIn(USERFLOW_SESSION_KEY, self.request.session)
        self.assertEqual(
            self.request.session.get(USERFLOW_SESSION_KEY, {}).get(
                "statistics_requested"
            ),
            True,
        )

    def test_get(self):
        self.request.session[USERFLOW_SESSION_KEY] = {
            "statistics_requested": False,
            "request_id": None,
        }
        manager = UserflowSessionManager.from_request(self.request)
        state = manager.get()
        self.assertEqual(state.statistics_requested, False)
        self.assertEqual(state.request_id, None)

    def test_update(self):
        self.request.session[USERFLOW_SESSION_KEY] = {
            "statistics_requested": False,
            "request_id": None,
        }
        manager = UserflowSessionManager.from_request(self.request)
        new_uuid = uuid.uuid4()
        state = manager.update(statistics_requested=True, request_id=new_uuid)

        self.assertEqual(state.statistics_requested, True)
        self.assertEqual(state.request_id, new_uuid)

        self.assertEqual(
            self.request.session.get(USERFLOW_SESSION_KEY, {}).get(
                "statistics_requested"
            ),
            True,
        )
        self.assertEqual(
            self.request.session.get(USERFLOW_SESSION_KEY, {}).get("request_id"),
            str(new_uuid),
        )

    def test_reset(self):
        self.request.session[USERFLOW_SESSION_KEY] = {
            "statistics_requested": True,
            "request_id": uuid.uuid4(),
        }
        manager = UserflowSessionManager.from_request(self.request)
        state = manager.reset()

        self.assertEqual(state.statistics_requested, False)
        self.assertEqual(state.request_id, None)

        self.assertEqual(
            self.request.session.get(USERFLOW_SESSION_KEY, {}).get(
                "statistics_requested"
            ),
            False,
        )
        self.assertEqual(
            self.request.session.get(USERFLOW_SESSION_KEY, {}).get("request_id"), None
        )

    def test_delete(self):
        self.request.session[USERFLOW_SESSION_KEY] = {
            "statistics_requested": False,
            "request_id": None,
        }
        manager = UserflowSessionManager.from_request(self.request)
        manager.delete()

        self.assertNotIn(USERFLOW_SESSION_KEY, manager._request_session)
        self.assertNotIn(USERFLOW_SESSION_KEY, self.request.session)
