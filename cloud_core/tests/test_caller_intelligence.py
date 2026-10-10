from __future__ import annotations

import tempfile
from pathlib import Path
import unittest

from cloud_core.app.caller_intelligence import (
    CallerCache,
    CallerIntelResult,
    classify_abstract_payload,
    normalize_phone_number,
)


class CallerIntelligenceTests(unittest.TestCase):
    def test_normalizes_israeli_mobile(self):
        self.assertEqual(
            normalize_phone_number("052-123-4567"),
            "+972521234567",
        )

    def test_preserves_international_number(self):
        self.assertEqual(
            normalize_phone_number("+44 20 7946 0958"),
            "+442079460958",
        )

    def test_spam_is_not_fraud(self):
        result = classify_abstract_payload(
            "+972521234567",
            {
                "valid": True,
                "is_spam": True,
                "risk_score": 0.20,
            },
        )
        self.assertEqual(result.category, "spam")
        self.assertTrue(result.spam)
        self.assertFalse(result.fraud)
        self.assertEqual(result.recommendation, "inform")

    def test_high_risk_without_fraud_flag_is_suspicious(self):
        result = classify_abstract_payload(
            "+972521234567",
            {
                "valid": True,
                "risk_score": 0.91,
            },
        )
        self.assertEqual(result.category, "suspicious")
        self.assertFalse(result.fraud)
        self.assertTrue(result.suspicious)
        self.assertEqual(result.recommendation, "warn")

    def test_explicit_fraud_gets_strong_warning(self):
        result = classify_abstract_payload(
            "+972521234567",
            {
                "valid": True,
                "is_fraud": True,
                "risk_score": 0.99,
            },
        )
        self.assertEqual(result.category, "fraud")
        self.assertTrue(result.fraud)
        self.assertEqual(result.recommendation, "warn_strong")

    def test_registered_name_is_identified(self):
        result = classify_abstract_payload(
            "+972521234567",
            {
                "valid": True,
                "phone_registration": {"name": "Example Person"},
            },
        )
        self.assertEqual(result.category, "identified")
        self.assertEqual(result.name, "Example Person")

    def test_cache_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CallerCache(Path(tmp) / "caller.sqlite3")
            original = CallerIntelResult(
                phone="+972521234567",
                name="Example Person",
                category="identified",
                confidence=0.75,
                provider="abstract",
                source="provider",
                recommendation="normal",
            )
            cache.put(original, ttl_days=30)
            loaded = cache.get(original.phone)

            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.phone, original.phone)
            self.assertEqual(loaded.name, original.name)
            self.assertEqual(loaded.source, "cache")


    def test_remembered_caller_is_returned_locally(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CallerCache(Path(tmp) / "caller.sqlite3")
            cache.remember_caller(
                "052-123-4567",
                name="Moshe Garage",
                label="trusted",
            )

            learned = cache.get_learned("0521234567")

            self.assertIsNotNone(learned)
            self.assertEqual(learned.name, "Moshe Garage")
            self.assertEqual(learned.category, "identified")
            self.assertEqual(learned.source, "user_confirmed")
            self.assertEqual(learned.provider, "jarvis_local")

    def test_learned_spam_is_not_fraud(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CallerCache(Path(tmp) / "caller.sqlite3")
            result = cache.remember_caller(
                "052-123-4567",
                label="spam",
            )

            self.assertTrue(result.spam)
            self.assertFalse(result.fraud)
            self.assertEqual(result.category, "spam")
            self.assertEqual(result.recommendation, "inform")

    def test_learned_fraud_is_strong_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CallerCache(Path(tmp) / "caller.sqlite3")
            result = cache.remember_caller(
                "052-123-4567",
                label="fraud",
            )

            self.assertTrue(result.fraud)
            self.assertFalse(result.spam)
            self.assertEqual(result.category, "fraud")
            self.assertEqual(result.recommendation, "warn_strong")

    def test_forget_learned_caller(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = CallerCache(Path(tmp) / "caller.sqlite3")
            cache.remember_caller(
                "052-123-4567",
                name="Temporary Caller",
            )

            self.assertTrue(cache.forget_caller("0521234567"))
            self.assertIsNone(cache.get_learned("0521234567"))



if __name__ == "__main__":
    unittest.main()
