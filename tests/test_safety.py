"""Regression tests for safe defaults and evidence retrieval."""
import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.core import answer, search, build_documents
from app.main import app


class RetrievalSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        build_documents()
        cls.client = TestClient(app)

    def test_default_request_works_without_api_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": ""}):
            response = self.client.post("/api/ask", json={"question": "Inspect SIM-MSN-10042"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "retrieval")

    def test_unmatched_id_has_no_citations(self):
        result = answer("SIM-MSN-99999", False)
        self.assertFalse(result["grounded"])
        self.assertEqual(result["citations"], [])

    def test_aircraft_identifier_is_exact(self):
        results = search("Inspect SIM-MSN-10042")
        self.assertEqual([r["aircraft_id"] for r in results], ["SIM-MSN-10042"])

    def test_no_meaningful_terms_returns_no_documents(self):
        self.assertEqual(search("What are the aircraft quality records?"), [])

    def test_generated_answers_not_claimed_verified(self):
        with patch("app.core.gemini_answer", return_value="Unverified generated text"):
            result = answer("Inspect SIM-MSN-10042", True)
        self.assertFalse(result["grounded"])
        self.assertIn("warning", result)
        self.assertEqual(result["mode"], "gemini")

    def test_home_defaults_to_retrieval(self):
        html = self.client.get("/").text
        self.assertIn('id="gemini"', html)
        self.assertNotIn('id="gemini" type="checkbox" checked', html)


if __name__ == "__main__":
    unittest.main()
