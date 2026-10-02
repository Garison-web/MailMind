import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app.main import consume_gmail_state, remember_gmail_state
from app.services import gmail


class GmailRedirectUriTests(unittest.TestCase):
    def test_redirect_uri_uses_app_base_url(self):
        with patch.dict(os.environ, {"APP_BASE_URL": "http://127.0.0.1:8001"}, clear=False):
            self.assertEqual(
                gmail.redirect_uri(),
                "http://127.0.0.1:8001/auth/gmail/callback",
            )

    def test_redirect_uri_defaults_to_localhost_8000(self):
        with patch.dict(os.environ, {}, clear=False):
            self.assertEqual(
                gmail.redirect_uri(),
                "http://127.0.0.1:8000/auth/gmail/callback",
            )

    def test_multiple_gmail_state_requests_are_accepted_once(self):
        request = SimpleNamespace(session={})
        remember_gmail_state(request, "state-one")
        remember_gmail_state(request, "state-two")
        self.assertTrue(consume_gmail_state(request, "state-two"))
        self.assertFalse(consume_gmail_state(request, "state-two"))
        self.assertFalse(consume_gmail_state(request, "state-one"))


if __name__ == "__main__":
    unittest.main()
