import json
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from cryptography.fernet import Fernet

from agent.chatgpt_plan import PlanError
from agent.jarvis_agent import JarvisAgent
from agent.plan_store import BrainError, PlanStore
from agent.private_brain import LocalChat, PrivateBrain, SMOKE_QUESTION
from agent.private_memory import PrivateMemory


class PrivateRoutingTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        key = Fernet.generate_key()
        self.store = PlanStore(self.root / "provider.db", lambda create: key)
        self.plan = Mock()
        self.session = {"client_id": "issued-id", "sub": "verified-user", "plan_type": "plus",
                        "scopes": ["openid", "resource.invoke", "chatgpt.tokens.use.direct", "offline_access"],
                        "access_token": "fictional-access", "refresh_token": "fictional-refresh",
                        "id_token": "fictional-identity", "expires_at": time.time() + 1000}
        self.plan.login.return_value = dict(self.session)
        self.plan.models.return_value = [("test-slug", "Model from account")]
        self.plan.respond.return_value = "READY"
        self.local = Mock(return_value="Local answer")
        self.memory = PrivateMemory(self.root / "memory.db")
        self.brain = self.instance()

    def instance(self):
        return PrivateBrain(store=self.store, memory=self.memory, plan=self.plan, local=self.local)

    def enable(self):
        self.brain.connect()
        self.brain.confirm_cost(True)
        self.brain.set_enabled(True)

    def test_cost_default_disabled_without_grant_or_confirmation(self):
        for fn in [self.brain.smoke, lambda: self.brain.confirm_cost(True),
                   lambda: self.brain.set_enabled(True)]:
            with self.assertRaises(BrainError):
                fn()
        self.brain.connect()
        self.assertTrue(self.brain.status()["connected"])
        with self.assertRaises(BrainError):
            self.brain.set_enabled(True)
        with self.assertRaises(BrainError):
            self.brain.set_model("guessed")
        self.assertEqual("Local answer", self.brain.ask("", "Hello"))
        self.assertEqual("qwen", self.local.call_args.args[0])
        self.plan.respond.assert_not_called()

    def test_consent_never_crosses_process_or_new_login(self):
        self.enable()
        other = self.instance()
        self.assertFalse(other.status()["enabled"])
        with self.assertRaises(BrainError):
            other.smoke()
        other.connect()
        other.confirm_cost(True)
        other.set_enabled(True)
        with self.assertRaises(BrainError):
            self.brain.smoke()
        self.assertEqual("READY", other.smoke())
        self.plan.respond.assert_called_once_with(self.session, "test-slug", SMOKE_QUESTION, "")
        self.assertEqual([], self.memory.list_conversations(""))

    def test_scope_and_workspace_fail_closed(self):
        self.plan.login.return_value.update(scopes=["openid"])
        with self.assertRaisesRegex(BrainError, "permission"):
            self.brain.connect()
        self.plan.models.assert_not_called()
        self.plan.login.return_value = dict(self.session, plan_type="business")
        self.brain.connect()
        with self.assertRaises(BrainError):
            self.brain.confirm_cost(True)
        self.plan.respond.assert_not_called()

    def test_native_agent_sends_only_project_excerpts_and_opt_in_saves(self):
        self.enable()
        self.memory.save_turn("a", "bicycle color", "ochre", enabled=True)
        self.memory.save_turn("b", "bicycle top secret", "green", enabled=True)
        agent = object.__new__(JarvisAgent)
        agent.private_brain = self.brain
        self.assertEqual("READY", agent.process_private("a", "Which bicycle?"))
        excerpt = self.plan.respond.call_args.args[-1]
        self.assertIn("bicycle color", excerpt)
        self.assertNotIn("secret", excerpt)
        self.assertEqual(1, len(self.memory.list_conversations("a")))
        self.brain.set_remember(True)
        agent.process_private("a", "What color is the bicycle?")
        self.assertEqual(2, len(self.memory.list_conversations("a")))
        self.assertEqual(1, len(self.memory.list_conversations("b")))
        self.local.assert_not_called()

    def test_plan_limit_pauses_requests_and_gemma_follows_qwen(self):
        self.enable()
        self.plan.respond.side_effect = PlanError("limit", "Plan limit reached.")
        self.local.side_effect = [BrainError("Qwen unavailable."), "Gemma reply", "Next Qwen reply"]
        self.assertEqual("Gemma reply", self.brain.ask("", "Question"))
        self.assertEqual(["qwen", "gemma"], [c.args[0] for c in self.local.call_args_list])
        self.assertEqual("Gemma", self.brain.status()["active"])
        self.assertIn("limit", self.brain.status()["error"])
        self.assertEqual("Next Qwen reply", self.brain.ask("", "Question again"))
        self.plan.respond.assert_called_once()
        with self.assertRaisesRegex(BrainError, "limit"):
            self.brain.set_enabled(True)
        self.brain.set_fallback(False)
        with self.assertRaisesRegex(BrainError, "limit"):
            self.brain.ask("", "Question")

    def test_plan_limit_survives_a_concurrent_token_rotation(self):
        self.enable()

        def late_limit(*args):
            with self.store.edit() as state:
                self.store.write_session(state, dict(self.session, access_token="rotated"))
            raise PlanError("limit", "Plan limit reached.")

        self.plan.respond.side_effect = late_limit
        self.assertEqual("Local answer", self.brain.ask("", "first"))
        self.assertEqual("Local answer", self.brain.ask("", "second"))
        self.assertFalse(self.brain.status()["enabled"])
        self.plan.respond.assert_called_once()

    def test_previous_grant_cannot_replace_new_catalog_for_the_same_client(self):
        self.enable()

        def late_catalog(*args):
            self.plan.models.side_effect = None
            self.plan.models.return_value = [("new", "New grant")]
            self.instance().connect()
            return [("old", "Old grant")]

        self.plan.models.side_effect = late_catalog
        with self.assertRaisesRegex(BrainError, "connection changed"):
            self.brain.refresh_models()
        self.assertEqual("new", self.brain.status()["model"])

    def test_empty_account_catalog_disables_plan_and_preserves_local_fallback(self):
        self.enable()
        self.plan.models.return_value = []
        self.brain.refresh_models()
        self.assertFalse(self.brain.status()["enabled"])
        with self.assertRaises(BrainError):
            self.brain.smoke()
        self.assertEqual("Local answer", self.brain.ask("", "hello"))
        self.plan.respond.assert_not_called()

    def test_lost_plan_scope_on_refresh_pauses_inference(self):
        self.enable()
        self.plan.refresh.return_value = dict(self.session, scopes=["openid"])
        with self.store.edit() as state:
            self.store.write_session(state, dict(self.session, expires_at=time.time() - 1))
        self.assertEqual("Local answer", self.brain.ask("", "hello"))
        self.assertFalse(self.brain.status()["enabled"])
        self.assertIn("permission", self.brain.status()["blocked"])
        self.plan.respond.assert_not_called()

    def test_smoke_does_not_substitute_local_answer(self):
        self.enable()
        self.plan.respond.side_effect = PlanError("network", "OpenAI unavailable.")
        with self.assertRaisesRegex(BrainError, "unavailable"):
            self.brain.smoke()
        self.local.assert_not_called()

    def test_refresh_rotation_is_atomic_across_instances(self):
        self.enable()
        rotated = dict(self.session, access_token="replacement-access", refresh_token="replacement-refresh")
        self.plan.refresh.return_value = rotated
        with self.store.edit() as state:
            self.store.write_session(state, dict(self.session, expires_at=time.time() - 1))
        with ThreadPoolExecutor(2) as pool:
            self.assertEqual([None, None], list(pool.map(lambda b: b.refresh_models(), [self.brain, self.instance()])))
        self.plan.refresh.assert_called_once()
        self.assertEqual("READY", self.brain.smoke())
        self.assertEqual(rotated, self.plan.respond.call_args.args[0])
        for raw in (b"replacement-access", b"replacement-refresh", b"fictional-identity"):
            self.assertNotIn(raw, self.store.path.read_bytes())

    def test_revoked_refresh_and_failed_logout_disable_cloud(self):
        self.enable()
        with self.store.edit() as state:
            self.store.write_session(state, dict(self.session, expires_at=time.time() - 1))
        self.plan.refresh.side_effect = PlanError("revoked", "Reconnect to ChatGPT.")
        with self.assertRaisesRegex(BrainError, "Reconnect"):
            self.brain.smoke()
        self.assertFalse(self.brain.status()["connected"])
        self.enable()
        self.plan.revoke.side_effect = PlanError("network", "offline")
        with self.assertRaisesRegex(BrainError, "revocation"):
            self.brain.disconnect()
        self.assertFalse(self.brain.status()["connected"])
        with self.store.edit() as state:
            self.assertEqual({"sub", "client_id"}, set(self.store.read_session(state)))
        self.plan.respond.assert_not_called()

    def test_keyring_failure_does_not_open_browser(self):
        def locked(create):
            raise BrainError("Vault is locked.")
        self.store.key = locked
        with self.assertRaisesRegex(BrainError, "locked"):
            self.brain.connect()
        self.plan.login.assert_not_called()
        self.assertEqual("Local answer", self.brain.ask("", "Hello"))

    def test_failed_first_exchange_keeps_issued_registration_for_recovery(self):
        def interrupted(host, previous, *, on_registration):
            on_registration("issued-id")
            raise PlanError("invalid", "Start a fresh sign-in.")
        self.plan.login.side_effect = interrupted
        with self.assertRaises(BrainError):
            self.brain.connect()
        self.assertFalse(self.brain.status()["connected"])
        self.plan.login.side_effect = None
        self.brain.connect()
        self.assertEqual({"client_id": "issued-id"}, self.plan.login.call_args.args[1])

    def test_successful_fallback_explains_why_connected_chatgpt_was_skipped(self):
        self.brain.connect()
        self.assertEqual("Local answer", self.brain.ask("", "Hello"))
        self.assertIn("off", self.brain.status()["error"])
        self.plan.respond.assert_not_called()

    def test_local_transport_pins_loopback_and_never_follows_redirects(self):
        with patch("agent.private_brain.http.client.HTTPConnection") as factory:
            for url in ["https://api.openai.com/v1", "http://localhost@external/v1", "http://localhost/v1?key=x"]:
                with self.assertRaises(BrainError):
                    LocalChat(url).request("models")
            factory.assert_not_called()
            response = factory.return_value.getresponse.return_value
            response.status = 307
            with self.assertRaises(BrainError):
                LocalChat("http://localhost:1234/v1").request("models")
            factory.assert_called_once_with("127.0.0.1", 1234, timeout=5)
            response.read.assert_not_called()

    def test_only_configured_local_family_is_requested(self):
        local = LocalChat("http://127.0.0.1:1234/v1", "jarvis-qwen")
        with patch.object(local, "request", side_effect=[
                {"data": [{"id": "other"}, {"id": "jarvis-qwen"}]},
                {"model": "jarvis-qwen", "choices": [{"message": {"content": "answer"}}]}]) as req, \
                patch("agent.private_brain.require_local_ai_available"):
            self.assertEqual("answer", local("qwen", "question", "excerpt"))
        payload = req.call_args.args[1]
        self.assertEqual("jarvis-qwen", payload["model"])
        self.assertNotIn("tools", payload)
        self.assertIn("excerpt", json.dumps(payload))

    def test_malformed_qwen_response_still_reaches_gemma(self):
        local = LocalChat("http://127.0.0.1:1234/v1", "qwen")
        self.brain.local = local
        roster = {"data": [{"id": "qwen"}, {"id": "gemma"}]}
        with patch.object(local, "request", side_effect=[
                roster, [], roster, {"choices": [{"message": {"content": "Gemma answer"}}]}]), \
                patch("agent.private_brain.require_local_ai_available"):
            self.assertEqual("Gemma answer", self.brain.ask("", "test"))
        self.assertEqual("Gemma", self.brain.status()["active"])
