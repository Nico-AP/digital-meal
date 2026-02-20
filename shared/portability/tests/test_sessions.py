from django.http import HttpResponse
from django.test import TestCase
from django.views import View

from shared.portability.constants import PortabilityContexts
from shared.portability.sessions import (
    PortabilitySession,
    PortabilitySessionManager,
    PortabilitySessionMixin,
)
from shared.portability.tests.utils import get_request_with_session


class TestPortabilitySession(TestCase):
    def test_default_values_are_none(self):
        session = PortabilitySession()

        self.assertIsNone(session.context)
        self.assertIsNone(session.state_token)
        self.assertIsNone(session.tiktok_open_id)

    def test_post_init_converts_string_context_to_enum(self):
        session = PortabilitySession(context="DM_EDU")

        self.assertIsInstance(session.context, PortabilityContexts)
        self.assertEqual(session.context, PortabilityContexts.DM_EDU)

    def test_post_init_leaves_none_context_unchanged(self):
        session = PortabilitySession(context=None)

        self.assertIsNone(session.context)

    def test_post_init_leaves_enum_context_unchanged(self):
        session = PortabilitySession(context=PortabilityContexts.MY_DM)

        self.assertEqual(session.context, PortabilityContexts.MY_DM)


class TestPortabilitySessionManager(TestCase):
    def setUp(self):
        self.request = get_request_with_session()
        self.manager = PortabilitySessionManager.from_request(self.request)

    def _seed_session(self, **kwargs):
        """Seed the portability session dict directly in the request session."""
        data = {"context": None, "state_token": None, "tiktok_open_id": None}
        data.update(kwargs)
        self.request.session[PortabilitySessionManager.SESSION_KEY] = data
        self.request.session.save()

    # --- from_request ---

    def test_from_request_returns_manager_instance(self):
        manager = PortabilitySessionManager.from_request(self.request)

        self.assertIsInstance(manager, PortabilitySessionManager)

    # --- get ---

    def test_get_returns_none_when_no_session(self):
        self.assertIsNone(self.manager.get())

    def test_get_returns_portability_session_when_session_exists(self):
        self._seed_session(state_token="tok")
        result = self.manager.get()

        self.assertIsInstance(result, PortabilitySession)
        self.assertEqual(result.state_token, "tok")

    # --- initialize ---

    def test_initialize_creates_session_when_absent(self):
        self.assertNotIn(PortabilitySessionManager.SESSION_KEY, self.request.session)
        self.manager.initialize()

        self.assertIn(PortabilitySessionManager.SESSION_KEY, self.request.session)

    def test_initialize_returns_existing_session_when_present(self):
        self._seed_session(state_token="existing")
        result = self.manager.initialize()

        self.assertEqual(result.state_token, "existing")

    # --- get_token ---

    def test_get_token_returns_none_when_no_session(self):
        self.assertIsNone(self.manager.get_token())

    def test_get_token_returns_token(self):
        self._seed_session(state_token="mytoken")

        self.assertEqual(self.manager.get_token(), "mytoken")

    # --- get_context ---

    def test_get_context_returns_none_when_no_session(self):
        self.assertIsNone(self.manager.get_context())

    def test_get_context_returns_context_as_enum(self):
        self._seed_session(context="DM_EDU")

        self.assertEqual(self.manager.get_context(), PortabilityContexts.DM_EDU)

    # --- get_tiktok_open_id ---

    def test_get_tiktok_open_id_returns_none_when_no_session(self):
        self.assertIsNone(self.manager.get_tiktok_open_id())

    def test_get_tiktok_open_id_returns_open_id(self):
        self._seed_session(tiktok_open_id="user123")

        self.assertEqual(self.manager.get_tiktok_open_id(), "user123")

    # --- update ---

    def test_update_creates_session_when_absent(self):
        self.manager.update(state_token="new")

        self.assertEqual(self.manager.get_token(), "new")

    def test_update_updates_target_field(self):
        self._seed_session(state_token="old")
        self.manager.update(state_token="new")

        self.assertEqual(self.manager.get_token(), "new")

    def test_update_preserves_other_fields(self):
        self._seed_session(tiktok_open_id="user123", state_token="tok")
        self.manager.update(state_token="new-tok")

        self.assertEqual(self.manager.get_tiktok_open_id(), "user123")

    def test_update_marks_session_modified(self):
        self.manager.update(state_token="tok")

        self.assertTrue(self.request.session.modified)

    def test_update_raises_for_unsupported_key(self):
        with self.assertRaises(TypeError):
            self.manager.update(non_existent_field="test")

    # --- reset ---

    def test_reset_clears_all_fields(self):
        self._seed_session(state_token="tok", tiktok_open_id="user", context="DM_EDU")
        result = self.manager.reset()

        self.assertIsNone(result.state_token)
        self.assertIsNone(result.tiktok_open_id)
        self.assertIsNone(result.context)

    # --- delete ---

    def test_delete_removes_session_key(self):
        self._seed_session()
        self.manager.delete()

        self.assertNotIn(PortabilitySessionManager.SESSION_KEY, self.request.session)

    def test_delete_is_noop_when_no_session(self):
        self.manager.delete()  # should not raise

    # --- delete_token ---

    def test_delete_token_clears_state_token_only(self):
        self._seed_session(state_token="tok", tiktok_open_id="user")
        self.manager.delete_token()
        session = self.manager.get()

        self.assertIsNone(session.state_token)
        self.assertEqual(session.tiktok_open_id, "user")


class TestPortabilitySessionMixin(TestCase):
    def setUp(self):
        class TestView(PortabilitySessionMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("OK")

        self.view = TestView()
        self.request = get_request_with_session()

    def test_dispatch_initializes_port_session(self):
        self.view.dispatch(self.request)

        self.assertIsInstance(self.view.port_session, PortabilitySessionManager)

    def test_dispatch_calls_super_and_returns_response(self):
        response = self.view.dispatch(self.request)

        self.assertEqual(response.status_code, 200)
