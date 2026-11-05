import json

import requests
import responses
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from responses import matchers


@override_settings(
    SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies',
    TURNSTILE_SECRET_KEY='test-secret',
    TURNSTILE_API_URL='https://localhost/verify',
    TURNSTILE_API_TIMEOUT=5,
    TURNSTILE_SESSION_EXPIRY_MINUTES=10,
)
class TestTurnstileRequests(SimpleTestCase):
    def test_success_sends_form_fields_and_sets_session(self) -> None:
        """
        Checks Requests encodes verification fields and the view records a successful verification.
        """
        with responses.RequestsMock() as remote:
            remote.post(
                'https://localhost/verify',
                json={'success': True},
                match=[
                    matchers.urlencoded_params_matcher(
                        {'secret': 'test-secret', 'response': 'test-token', 'remoteip': '127.0.0.1'}
                    ),
                    matchers.request_kwargs_matcher({'timeout': 5}),
                ],
            )
            response = self.client.post(reverse('turnstile-verify'), {'token': 'test-token'})
            self.assertEqual(len(remote.calls), 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content), {'ok': True})
        self.assertTrue(self.client.session['turnstile_verified'])
        self.assertEqual(self.client.session.get_expiry_age(), 600)

    def test_rejection_and_timeout_leave_session_unverified(self) -> None:
        """
        Checks unsuccessful verification and a Requests timeout both deny access without retrying.
        """
        cases = [
            ({'json': {'success': False, 'error-codes': ['invalid-test-token']}}, ['invalid-test-token']),
            ({'body': requests.Timeout('test timeout')}, 'timeout'),
        ]
        for response_args, reason in cases:
            with self.subTest(reason=reason), responses.RequestsMock() as remote:
                remote.post('https://localhost/verify', **response_args)
                response = self.client.post(reverse('turnstile-verify'), {'token': 'test-token'})
                self.assertEqual(len(remote.calls), 1)
                self.assertEqual(response.status_code, 403)
                self.assertEqual(json.loads(response.content), {'ok': False, 'reason': reason})
                self.assertNotIn('turnstile_verified', self.client.session)

    def test_missing_token_does_not_send_a_request(self) -> None:
        """
        Checks an empty submission is rejected before Requests is called.
        """
        with responses.RequestsMock() as remote:
            response = self.client.post(reverse('turnstile-verify'), {})
            self.assertEqual(len(remote.calls), 0)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('turnstile_verified', self.client.session)
