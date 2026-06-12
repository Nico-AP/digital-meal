from datetime import UTC, datetime

from django.contrib.sessions.middleware import SessionMiddleware
from django.test import RequestFactory, SimpleTestCase, TestCase

from mydigitalmeal.studies.constants import STUDIES_SESSION_KEY
from mydigitalmeal.studies.sessions import (
    StudyParticipationSession,
    StudyParticipationSessionManager,
)


class TestStudyParticipationSession(SimpleTestCase):
    def test_default_values(self):
        session = StudyParticipationSession()

        self.assertEqual(session.url_parameters, {})
        self.assertIsNone(session.ddm_project_id)
        self.assertIsNone(session.method)
        self.assertIsNone(session.enroll_time)

    def test_to_dict_roundtrip_populated(self):
        original = StudyParticipationSession(
            url_parameters={"utm": "a"},
            ddm_project_id="p123",
            method="port-api",
            enroll_time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        )

        retrieved = StudyParticipationSession.from_dict(original.to_dict())

        self.assertEqual(retrieved, original)

    def test_to_dict_roundtrip_empty(self):
        original = StudyParticipationSession()

        retrieved = StudyParticipationSession.from_dict(original.to_dict())

        self.assertEqual(retrieved, original)

    def test_from_dict_handles_missing_enroll_time(self):
        session = StudyParticipationSession.from_dict({"ddm_project_id": "p"})

        self.assertIsNone(session.enroll_time)

    def test_from_dict_handles_iso_string_enroll_time(self):
        iso = "2024-01-01T12:00:00+00:00"

        session = StudyParticipationSession.from_dict({"enroll_time": iso})

        self.assertIsInstance(session.enroll_time, datetime)
        self.assertEqual(session.enroll_time.isoformat(), iso)

    def test_from_dict_ignores_unknown_keys(self):
        session = StudyParticipationSession.from_dict(
            {"ddm_project_id": "p", "bogus": "ignored"},
        )

        self.assertEqual(session.ddm_project_id, "p")

    def test_to_dict_serializes_none_enroll_time(self):
        session = StudyParticipationSession()

        as_dict = session.to_dict()

        self.assertIn("enroll_time", as_dict)
        self.assertIsNone(as_dict["enroll_time"])


class TestStudyParticipationSessionManager(TestCase):
    def setUp(self):
        self.request = RequestFactory().get("/")
        middleware = SessionMiddleware(get_response=lambda r: None)
        middleware.process_request(self.request)
        self.request.session.save()

    def test_from_request_wires_session(self):
        manager = StudyParticipationSessionManager.from_request(self.request)

        self.assertIs(manager._request_session, self.request.session)

    def test_get_returns_none_when_session_key_absent(self):
        manager = StudyParticipationSessionManager.from_request(self.request)

        self.assertIsNone(manager.get())

    def test_get_returns_dataclass_when_present(self):
        self.request.session[STUDIES_SESSION_KEY] = {
            "ddm_project_id": "p",
            "method": "port-api",
        }
        manager = StudyParticipationSessionManager.from_request(self.request)

        state = manager.get()

        self.assertIsInstance(state, StudyParticipationSession)
        self.assertEqual(state.ddm_project_id, "p")
        self.assertEqual(state.method, "port-api")

    def test_initialize_creates_session_when_absent(self):
        manager = StudyParticipationSessionManager.from_request(self.request)

        state = manager.initialize()

        self.assertIsInstance(state, StudyParticipationSession)
        self.assertIn(STUDIES_SESSION_KEY, self.request.session)
        self.assertTrue(self.request.session.modified)

    def test_initialize_does_not_overwrite_existing(self):
        self.request.session[STUDIES_SESSION_KEY] = {"ddm_project_id": "keep"}
        manager = StudyParticipationSessionManager.from_request(self.request)

        state = manager.initialize()

        self.assertEqual(state.ddm_project_id, "keep")

    def test_update_creates_session_if_missing(self):
        # TODO: Doublecheck
        # Documents current (intentional) behaviour: ``update`` silently
        # bootstraps a session if none exists. Flagged as a
        # potential foot-gun; pinning the behaviour here so a future
        # change is a deliberate decision.
        manager = StudyParticipationSessionManager.from_request(self.request)

        state = manager.update(ddm_project_id="p")

        self.assertEqual(state.ddm_project_id, "p")
        self.assertIn(STUDIES_SESSION_KEY, self.request.session)

    def test_update_merges_fields(self):
        manager = StudyParticipationSessionManager.from_request(self.request)
        manager.update(method="port-api")

        state = manager.update(ddm_project_id="p")

        self.assertEqual(state.method, "port-api")
        self.assertEqual(state.ddm_project_id, "p")

    def test_reset_replaces_with_defaults(self):
        self.request.session[STUDIES_SESSION_KEY] = {
            "ddm_project_id": "p",
            "method": "port-api",
        }
        manager = StudyParticipationSessionManager.from_request(self.request)

        state = manager.reset()

        self.assertIsNone(state.ddm_project_id)
        self.assertIsNone(state.method)
        self.assertIn(STUDIES_SESSION_KEY, self.request.session)

    def test_delete_removes_key(self):
        self.request.session[STUDIES_SESSION_KEY] = {"ddm_project_id": "p"}
        manager = StudyParticipationSessionManager.from_request(self.request)

        manager.delete()

        self.assertNotIn(STUDIES_SESSION_KEY, self.request.session)

    def test_delete_is_idempotent_when_absent(self):
        manager = StudyParticipationSessionManager.from_request(self.request)

        manager.delete()  # must not raise

        self.assertNotIn(STUDIES_SESSION_KEY, self.request.session)
