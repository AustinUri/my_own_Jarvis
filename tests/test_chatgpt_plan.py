import base64
from contextlib import contextmanager
import hashlib
import io
import json
import time
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from agent import chatgpt_plan as plan


def encoded(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def integer(value):
    return encoded(value.to_bytes((value.bit_length() + 7) // 8, "big"))


def event_stream(*events):
    return io.BytesIO(b"".join(b"data: " + json.dumps(event).encode() + b"\n\n" for event in events))


class IdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.private = rsa.generate_private_key(65537, 2048)
        public = cls.private.public_key().public_numbers()
        cls.keys = {"keys": [{"kid": "one", "kty": "RSA", "n": integer(public.n), "e": integer(public.e)}]}

    def setUp(self):
        self.client = plan.ChatGPTPlan()
        self.params, self.form = {}, {}
        self.overrides = {}
        self.scope = plan.SCOPES
        self.callback_override = {}
        self.redirect = "http://127.0.0.1:32000/auth/callback"
        self.calls = []
        self.patches = [patch.object(plan, "_browser_callback", side_effect=self.callback),
                        patch.object(self.client, "_json", side_effect=self.reply)]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def callback(self, params):
        self.params.update(params)
        values = dict(state=[params["state"]], code=["one-time-code"])
        if params["client_id"] == plan.DYNAMIC_CLIENT:
            values["client_id"] = ["issued"]
        values.update(self.callback_override)
        return self.redirect, values

    def sign(self):
        stamp = int(time.time())
        claims = dict(sub="acct", aud="issued", iss=plan.ISSUER, iat=stamp - 2,
                      exp=stamp + 3600, nonce=self.params["nonce"])
        claims.update(self.overrides)
        header = encoded(b'{"alg":"RS256","kid":"one"}')
        body = encoded(json.dumps(claims).encode())
        data = (header + "." + body).encode()
        return data.decode() + "." + encoded(self.private.sign(data, padding.PKCS1v15(), hashes.SHA256()))

    def reply(self, url, **kwargs):
        self.calls.append(url)
        if url == plan.DISCOVERY:
            return {"issuer": plan.ISSUER, "jwks_uri": plan.ISSUER + "/keys"}
        if url == plan.ISSUER + "/keys":
            return self.keys
        if url == plan.TOKEN:
            self.form.update(kwargs["form"])
            return {"token_type": "Bearer", "access_token": "access", "refresh_token": "refresh",
                    "id_token": self.sign(), "expires_in": 3600, "scope": self.scope}
        self.fail("Unexpected network destination")

    def test_initial_login_binds_pkce_state_nonce_and_issued_client(self):
        session = self.client.login("urn:uuid:local")
        expected = encoded(hashlib.sha256(self.form["code_verifier"].encode()).digest())
        self.assertEqual(self.params["code_challenge"], expected)
        self.assertEqual(self.params["code_challenge_method"], "S256")
        self.assertNotEqual(self.params["state"], self.params["nonce"])
        self.assertEqual(self.form["redirect_uri"], self.redirect)
        self.assertEqual(self.form["resource"], plan.RESOURCE)
        self.assertEqual(self.form["grant_type"], "authorization_code")
        self.assertEqual(self.params["agent_name_hint"], "JARVIS")
        self.assertEqual(self.params["client_id"], plan.DYNAMIC_CLIENT)
        self.assertEqual(self.form["client_id"], "issued")
        self.assertEqual(session["sub"], "acct")
        self.assertIn(plan.DIRECT_SCOPE, session["scopes"])

    def test_returning_registration_reuses_issued_client_and_identity_hint(self):
        session = self.client.login("host", {"client_id": "issued", "sub": "acct", "id_token": "prior"},
                                    on_registration=lambda _: self.fail("Registration should already exist"))
        self.assertEqual(self.params["client_id"], "issued")
        self.assertEqual(self.params["id_token_hint"], "prior")
        self.assertNotIn("agent_name_hint", self.params)
        self.assertEqual(session["client_id"], "issued")

    def test_invalid_code_keeps_pending_client_for_next_attempt(self):
        saved = []

        def reject_code(url, **kwargs):
            self.assertEqual(url, plan.TOKEN)
            self.assertEqual(saved, ["issued"])
            raise plan._service_error("invalid_grant", 400)

        with patch.object(self.client, "_json", side_effect=reject_code), self.assertRaises(plan.PlanError):
            self.client.login("host", on_registration=saved.append)
        first_challenge = self.params["code_challenge"]
        session = self.client.login("host", {"client_id": saved[0]}, on_registration=saved.append)
        self.assertEqual(saved, ["issued"])
        self.assertEqual(session["sub"], "acct")
        self.assertNotEqual(first_challenge, self.params["code_challenge"])

    def test_callback_rejected_before_exchange(self):
        for overrides in ({"state": ["different"]}, {"state": ["duplicate", "state"]},
                          {"client_id": [""]}, {"client_id": ["bad\nclient"]},
                          {"client_id": [plan.DYNAMIC_CLIENT]}, {"error": ["access_denied"]}):
            with self.subTest(overrides=overrides):
                self.callback_override = overrides
                with self.assertRaises(plan.PlanError):
                    self.client.login("host", on_registration=lambda _: self.fail("Callback was invalid"))
                self.assertEqual(self.calls, [])

    def test_reauthorization_cannot_switch_client_or_subject(self):
        self.callback_override = {"client_id": ["wrong"]}
        with self.assertRaises(plan.PlanError):
            self.client.login("host", {"client_id": "issued", "sub": "acct"})
        self.assertEqual(self.calls, [])
        self.callback_override.clear()
        with self.assertRaises(plan.PlanError):
            self.client.login("host", {"client_id": "issued", "sub": "different"})

    def test_invalid_signature_rejected(self):
        wrong = rsa.generate_private_key(65537, 2048)
        with patch.object(self, "private", wrong), self.assertRaises(plan.PlanError):
            self.client.login("host")

    def test_rejects_wrong_issuer_audience_authorized_party_nonce_and_expiry(self):
        for changes in ({"iss": "elsewhere"}, {"aud": "different"}, {"aud": ["issued", "also"]},
                        {"azp": "different"}, {"nonce": "another"}, {"exp": time.time() - 5},
                        {"nbf": time.time() + 600}, {"exp": float("nan")}):
            with self.subTest(changes=changes):
                self.overrides = changes
                with self.assertRaises(plan.PlanError):
                    self.client.login("host")

    def test_reduced_permission_preserves_identity_and_blocks_model_requests(self):
        self.scope = "openid profile email"
        session = self.client.login("host")
        self.assertEqual(session["sub"], "acct")
        before = len(self.calls)
        with self.assertRaises(plan.PlanError) as error:
            self.client.models(session)
        self.assertEqual(error.exception.kind, "permission")
        self.assertEqual(before, len(self.calls))

    def test_refresh_validates_any_replacement_identity_and_returned_nonce(self):
        session = self.client.login("host")
        self.assertEqual(self.client.refresh(session)["sub"], session["sub"])
        for bad in ({"nonce": "new-sign-in"}, {"sub": "another-user"}):
            with self.subTest(bad=bad):
                self.overrides = bad
                with self.assertRaises(plan.PlanError):
                    self.client.refresh(session)


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.client = plan.ChatGPTPlan()
        self.session = dict(scopes=plan.SCOPES.split(), access_token="access", refresh_token="original",
                            sub="acct", client_id="issued", expires_at=time.time() + 3600)

    def test_models_preserve_visible_account_order(self):
        with patch.object(self.client, "_json", return_value={"models": [
            {"slug": "three", "visibility": "hide", "display_name": "Three"},
            {"slug": "two", "visibility": "list", "display_name": "Two"},
            {"slug": "one", "visibility": "list", "display_name": "One"}]}) as mocked:
            self.assertEqual(self.client.models(self.session), [("two", "Two"), ("one", "One")])
        mocked.assert_called_once_with(plan.RESOURCE + "/models", headers={"Authorization": "Bearer access"})

    def test_expired_access_never_starts_inference(self):
        self.session["expires_at"] = time.time() - 1
        with patch.object(self.client, "_open") as request, self.assertRaises(plan.PlanError) as error:
            self.client.respond(self.session, "model", "question", "")
        self.assertEqual(error.exception.kind, "expired")
        request.assert_not_called()

    def test_malformed_bearer_never_enters_a_request_or_error_text(self):
        self.session["access_token"] = "secret\nvalue"
        with patch.object(self.client, "_open") as request, self.assertRaises(plan.PlanError) as error:
            self.client.models(self.session)
        self.assertNotIn("secret", str(error.exception))
        request.assert_not_called()

    def test_rotated_refresh_preserves_scope_and_subject_and_replaces_both_tokens(self):
        reply = dict(token_type="bearer", access_token="new access", refresh_token="new refresh", expires_in=60)
        with patch.object(self.client, "_json", return_value=reply) as request:
            updated = self.client.refresh(self.session)
        request.assert_called_once_with(plan.TOKEN, form=dict(grant_type="refresh_token", client_id="issued",
                                        refresh_token="original", resource=plan.RESOURCE))
        self.assertEqual(updated["refresh_token"], "new refresh")
        self.assertEqual(updated["access_token"], "new access")
        self.assertEqual(updated["sub"], "acct")
        self.assertEqual(updated["scopes"], self.session["scopes"])

    def test_refresh_before_earliest_is_blocked(self):
        self.session["earliest_refresh_at"] = time.time() + 3600
        with patch.object(self.client, "_open") as request, self.assertRaises(plan.PlanError):
            self.client.refresh(self.session)
        request.assert_not_called()

    def test_revocation_only_posts_to_validated_discovery_endpoint(self):
        for endpoint in ["http://auth.openai.com/revoke", "https://evil.invalid/revoke", "https://auth.openai.com@evil.invalid"]:
            with self.subTest(endpoint=endpoint), patch.object(self.client, "_json", return_value={
                    "issuer": plan.ISSUER, "revocation_endpoint": endpoint}), patch.object(self.client, "_open") as request:
                with self.assertRaises(plan.PlanError):
                    self.client.revoke(self.session)
                request.assert_not_called()
        endpoint = plan.ISSUER + "/revoke"
        with patch.object(self.client, "_json", return_value={"issuer": plan.ISSUER, "revocation_endpoint": endpoint}), \
                patch.object(self.client, "_open") as request:
            request.return_value.__enter__.return_value.status = 200
            self.client.revoke(self.session)
        request.assert_called_once_with(endpoint, form=dict(token="original", token_type_hint="refresh_token",
                                                           client_id="issued"))

    def test_stream_enforces_preview_contract_and_waits_for_completed(self):
        @contextmanager
        def fake_open(url, *, body, headers):
            self.assertEqual(url, plan.RESOURCE + "/responses")
            self.assertEqual(headers["Authorization"], "Bearer access")
            self.assertFalse(body["store"])
            self.assertTrue(body["stream"])
            self.assertEqual(body["model"], "selected")
            self.assertEqual(len(body["input"][0]["content"].removeprefix("Private reference excerpts:\n")), 4000)
            self.assertEqual(body["input"][-1], {"role": "user", "content": "question"})
            stream = event_stream({"type": "response.output_text.delta", "delta": "yes"},
                                  {"type": "response.completed"})
            from email.message import Message
            stream.headers = Message()
            stream.headers["Content-Type"] = "text/event-stream; charset=utf-8"
            yield stream

        with patch.object(self.client, "_open", side_effect=fake_open):
            self.assertEqual(self.client.respond(self.session, "selected", "question", "a" * 5000), "yes")

    def test_incomplete_or_failed_stream_discards_partial_answer(self):
        for kind, terminal in (("incomplete", []), ("incomplete", [{"type": "response.incomplete"}]),
                ("limit", [{"type": "response.failed", "response": {"error": {
                    "code": "subscription_sharing_usage_limit_exceeded", "message": "sensitive"}}}])):
            stream = event_stream({"type": "response.output_text.delta", "delta": "private"}, *terminal)
            with self.subTest(kind=kind), self.assertRaises(plan.PlanError) as error:
                plan._stream_answer(stream)
            self.assertEqual(error.exception.kind, kind)
            self.assertNotIn("private", str(error.exception))
            self.assertNotIn("sensitive", str(error.exception))

    def test_http_error_does_not_retry_or_echo_remote_detail(self):
        from urllib.error import HTTPError
        failure = HTTPError(plan.RESOURCE + "/models", 403, "No", {},
                            io.BytesIO(b'{"error":{"code":"subscription_sharing_user_not_eligible","message":"sensitive"}}'))
        with patch.object(self.client._opener, "open", side_effect=failure) as mocked:
            with self.assertRaises(plan.PlanError) as error:
                self.client.models(self.session)
        mocked.assert_called_once()
        self.assertEqual(error.exception.kind, "ineligible")
        self.assertNotIn("sensitive", str(error.exception))

    def test_redirect_handler_refuses_to_forward_credentials(self):
        self.assertIsNone(plan._NoRedirect().redirect_request(None, None, None, None, {}, "https://elsewhere.invalid"))
