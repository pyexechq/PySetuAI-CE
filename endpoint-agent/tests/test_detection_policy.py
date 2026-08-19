"""Unit tests for local secret detection and policy evaluation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pysetu_agent.detection import detect
from pysetu_agent.policy import LocalPolicy, PolicyCache, PolicyRule, evaluate, policy_from_payload


class DetectTest(unittest.TestCase):
    def test_detects_aws_access_key_and_redacts(self) -> None:
        result = detect("export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE")
        self.assertIn("AWS_ACCESS_KEY", result.classifications)
        self.assertIsNotNone(result.redacted_content)
        self.assertNotIn("AKIAIOSFODNN7EXAMPLE", result.redacted_content)

    def test_detects_private_key_header(self) -> None:
        result = detect("-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----")
        self.assertIn("PRIVATE_KEY", result.classifications)

    def test_detects_pii_ssn(self) -> None:
        result = detect("SSN: 123-45-6789")
        self.assertIn("SSN", result.classifications)
        self.assertNotIn("123-45-6789", result.redacted_content)

    def test_clean_content_has_no_findings(self) -> None:
        result = detect("print('hello world')")
        self.assertFalse(result.has_sensitive)
        self.assertIsNone(result.redacted_content)


class EvaluateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = LocalPolicy.defaults()

    def test_env_is_blocked(self) -> None:
        self.assertEqual(evaluate(self.policy, "/workspace/.env", ["GENERIC_SECRET"]), "block")

    def test_pem_is_blocked(self) -> None:
        self.assertEqual(evaluate(self.policy, "/workspace/keys/prod.pem", ["PRIVATE_KEY"]), "block")

    def test_secret_without_rule_defaults_to_block(self) -> None:
        self.assertEqual(evaluate(self.policy, "/tmp/notes.txt", ["AWS_ACCESS_KEY"]), "block")

    def test_pii_without_rule_defaults_to_redact(self) -> None:
        self.assertEqual(evaluate(self.policy, "/tmp/notes.txt", ["SSN"]), "redact")

    def test_allowed_path_overrides_classification(self) -> None:
        self.assertEqual(evaluate(self.policy, "/workspace/tests/fixtures.env", ["GENERIC_SECRET"]), "allow")

    def test_custom_rule_wins_by_rank(self) -> None:
        policy = LocalPolicy(rules=[PolicyRule("*.pem", "*", "approval"), PolicyRule("*.pem", "*", "block")])
        self.assertEqual(evaluate(policy, "prod.pem", ["PRIVATE_KEY"]), "block")


class PolicyCacheTest(unittest.TestCase):
    def test_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "policy.json")
            cache = PolicyCache(str(path))
            cache.save(LocalPolicy.defaults())
            loaded = cache.load()
            self.assertEqual(loaded.version, "1")
            self.assertTrue(any(rule.pattern == ".env" for rule in loaded.rules))

    def test_tamper_detection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "policy.json")
            cache = PolicyCache(str(path))
            cache.save(LocalPolicy.defaults())
            content = path.read_text()
            path.write_text(content.replace('"block"', '"allow"', 1))
            with self.assertRaises(ValueError):
                cache.load()

    def test_load_or_defaults_on_missing_file(self) -> None:
        cache = PolicyCache("/nonexistent/policy.json")
        policy = cache.load_or_defaults()
        self.assertTrue(any(rule.pattern == ".env" for rule in policy.rules))


class PolicyFromPayloadTest(unittest.TestCase):
    def test_builds_policy_from_control_plane_payload(self) -> None:
        payload = {
            "version": "3",
            "rules": [
                {"pattern": ".env", "classification": "*", "action": "block"},
                {"pattern": "src/**", "classification": "*", "action": "allow"},
            ],
        }
        policy = policy_from_payload(payload)
        self.assertEqual(policy.version, "3")
        self.assertEqual(evaluate(policy, "/repo/src/app.py", ["GENERIC_SECRET"]), "allow")
        self.assertEqual(evaluate(policy, "/repo/.env", ["GENERIC_SECRET"]), "block")


if __name__ == "__main__":
    unittest.main()
