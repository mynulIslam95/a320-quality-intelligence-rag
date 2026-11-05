import unittest
from fastapi.testclient import TestClient
from app.core import build_documents,search,answer,make_prompt
from app.main import app

class RagTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.count=build_documents()
        cls.client=TestClient(app)
    def test_generated_documents(self):self.assertEqual(self.count,120)
    def test_exact_aircraft(self):
        docs=search("What happened to SIM-MSN-10042?")
        self.assertEqual(len(docs),1)
        self.assertEqual(docs[0]["source"],"SIM-MSN-10042.md")
    def test_missing_aircraft_refusal(self):
        result=answer("What happened to SIM-MSN-99999?",False)
        self.assertFalse(result["grounded"])
        self.assertEqual(result["citations"],[])
    def test_evidence_citation(self):
        result=answer("Inspect SIM-MSN-10042",False)
        self.assertTrue(result["grounded"])
        self.assertEqual(result["citations"][0]["aircraft_id"],"SIM-MSN-10042")
    def test_prompt_instructions(self):
        self.assertIn("Use ONLY the sources",make_prompt("Test",search("SIM-MSN-10042")))
    def test_health(self):self.assertEqual(self.client.get("/api/health").status_code,200)
    def test_ask(self):
        response=self.client.post("/api/ask",json={"question":"Find SIM-MSN-10042","use_gemini":False})
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.json()["grounded"])
    def test_validation(self):
        self.assertEqual(self.client.post("/api/ask",json={"question":"x"}).status_code,422)
    def test_home(self):self.assertEqual(self.client.get("/").status_code,200)
if __name__=="__main__":unittest.main()
