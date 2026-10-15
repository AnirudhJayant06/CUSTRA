"""HTTP contract tests. Start the backend first; optionally set CUSTRA_TEST_URL."""
import json
import os
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


class ApiTests(unittest.TestCase):
    def request(self, path, payload=None):
        request = Request(
            os.environ.get("CUSTRA_TEST_URL", "http://127.0.0.1:8000") + path,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Content-Type": "application/json"},
        )
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response)

    def test_health(self):
        self.assertEqual(self.request("/api/health"), (200, {
            "status": "healthy", "service": "Custra Backend"}))

    def test_submission(self):
        status, body = self.request("/api/test-issue", {
            "product_name": " Samsung Washing Machine ",
            "description": " Water is leaking underneath. "})
        self.assertEqual(status, 200)
        self.assertEqual(body, {
            "success": True, "message": "Test issue submitted successfully!",
            "product_name": "Samsung Washing Machine",
            "description": "Water is leaking underneath.", "status": "received"})

    def test_invalid_submissions(self):
        for field, invalid_values in {
            "product_name": ["", " \t\n", "a" * 121, None, 42],
            "description": ["", " \t\n", "a" * 2001, None, 42],
        }.items():
            for value in invalid_values:
                with self.subTest(field=field, value=str(value)[:20]):
                    payload = {"product_name": "Washer", "description": "Leaking"}
                    payload[field] = value
                    self.assertEqual(self.request("/api/test-issue", payload)[0], 422)
        self.assertEqual(self.request("/api/test-issue", {})[0], 422)

    def test_length_boundaries(self):
        self.assertEqual(self.request("/api/test-issue", {
            "product_name": "a" * 120, "description": "a" * 2000})[0], 200)


if __name__ == "__main__":
    unittest.main()
