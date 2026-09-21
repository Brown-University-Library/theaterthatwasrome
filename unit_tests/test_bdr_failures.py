import json
import logging
import os
from unittest.mock import patch

import httpx2
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config.settings.base import positive_env_seconds
from rome_app import models
from rome_app.lib import bdr_client
from rome_app.lib.bdr_failure import SkipHandledBdrFailure
from unit_tests import responses_data
from unit_tests.http_mock import BdrMock


class TestBdrClient(SimpleTestCase):
    def test_timeout_configuration(self) -> None:
        """
        Checks defaults and fractional overrides on the actual outgoing HTTPX2 request.
        """
        for connect, read in [(5.0, 10.0), (0.25, 1.5)]:
            with (
                self.subTest(connect=connect),
                override_settings(BDR_CONNECT_TIMEOUT=connect, BDR_READ_TIMEOUT=read),
                BdrMock() as remote,
            ):
                remote.add('GET', 'https://localhost/api/search/', body='{}')
                bdr_client.request('GET', 'https://localhost/api/search/')
                self.assertEqual(
                    remote.calls[0].extensions['timeout'],
                    {'connect': connect, 'read': read, 'write': read, 'pool': connect},
                )

    def test_environment_values(self) -> None:
        """
        Checks missing values, fractional seconds, and invalid environment configuration.
        """
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(positive_env_seconds('ROME_BDR_CONNECT_TIMEOUT', 5.0), 5.0)
            self.assertEqual(positive_env_seconds('ROME_BDR_READ_TIMEOUT', 10.0), 10.0)
        with patch.dict(os.environ, {'ROME_BDR_READ_TIMEOUT': '2.5'}):
            self.assertEqual(positive_env_seconds('ROME_BDR_READ_TIMEOUT', 10.0), 2.5)
        for value in ['', 'bad', '0', '-1', 'nan', 'inf']:
            with (
                self.subTest(value=value),
                patch.dict(os.environ, {'ROME_BDR_READ_TIMEOUT': value}),
                self.assertRaises(ImproperlyConfigured),
            ):
                positive_env_seconds('ROME_BDR_READ_TIMEOUT', 10.0)

    def test_transport_failures_are_not_retried(self) -> None:
        """
        Checks that reads and writes stop after one failed network operation.
        """
        failures = [httpx2.ConnectTimeout, httpx2.ReadTimeout, httpx2.ConnectError, httpx2.RemoteProtocolError]
        for method in ['GET', 'POST', 'PUT']:
            for failure in failures:
                with self.subTest(method=method, failure=failure.__name__), BdrMock() as remote:
                    remote.add(method, 'https://localhost/api/items/', body=failure('Unavailable'))
                    with self.assertRaises(bdr_client.BdrUnavailable):
                        bdr_client.request(method, 'https://localhost/api/items/')
                    self.assertEqual(len(remote.calls), 1)

    def test_http_errors_remain_distinct(self) -> None:
        """
        Checks that service failures, missing records, and other HTTP errors stay distinct.
        """
        for status in [400, 401, 403, 404, 500, 502, 503, 504]:
            with self.subTest(status=status), BdrMock() as remote:
                remote.add('GET', 'https://localhost/api/items/', status=status)
                expected = bdr_client.BdrUnavailable if status >= 500 else httpx2.HTTPStatusError
                with self.assertRaises(expected):
                    bdr_client.request('GET', 'https://localhost/api/items/')
        with BdrMock() as remote:
            remote.add('GET', 'https://localhost/api/items/', status=404)
            response = bdr_client.request('GET', 'https://localhost/api/items/', allow_not_found=True)
            self.assertEqual(response.status_code, 404)

    def test_writes_do_not_follow_redirects(self) -> None:
        """
        Checks that an annotation write cannot be replayed by a redirect.
        """
        with patch(
            'httpx2.HTTPTransport.handle_request',
            return_value=httpx2.Response(
                307,
                headers={'Location': 'https://localhost/elsewhere/'},
            ),
        ) as transport:
            with self.assertRaises(httpx2.HTTPStatusError):
                bdr_client.request('POST', 'https://localhost/api/items/', data={'title': 'Example'})
            self.assertEqual(transport.call_count, 1)


@override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'], EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class TestBdrOutages(TestCase):
    def test_repeated_failures_send_no_mail_and_recover(self) -> None:
        """
        Checks real request logging during repeated outages and the next successful request.
        """
        url = f'https://localhost/api/collections/{settings.TTWR_COLLECTION_PID}/'
        with BdrMock() as remote:
            remote.add('GET', url, body=httpx2.ConnectTimeout('Unavailable'))
            for _ in range(3):
                response = self.client.get(reverse('books'))
                self.assertContains(response, 'temporarily unavailable', status_code=503)
                self.assertEqual(response['Retry-After'], '60')
                self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(len(remote.calls), 3)
            self.assertEqual(len(mail.outbox), 0)
            remote.reset()
            remote.add('GET', url, body=json.dumps({'items': {'numFound': 0, 'docs': []}}))
            response = self.client.get(reverse('books'))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, 'temporarily unavailable')

    def test_unexpected_failure_still_sends_mail(self) -> None:
        """
        Checks that invalid BDR data still produces an application error email.
        """
        with BdrMock() as remote:
            remote.add('GET', f'https://localhost/api/collections/{settings.TTWR_COLLECTION_PID}/', body='not JSON')
            response = self.client.get(reverse('books'))
            self.assertEqual(response.status_code, 500)
            self.assertEqual(len(mail.outbox), 1)

    def test_item_outages_are_not_missing_records(self) -> None:
        """
        Checks that book details distinguish an outage from a missing item.
        """
        for status in [404, 503]:
            with self.subTest(status=status), BdrMock() as remote:
                remote.add('GET', 'https://localhost/api/items/testsuite:123/', status=status)
                response = self.client.get(reverse('thumbnail_viewer', kwargs={'book_id': '123'}))
                self.assertEqual(response.status_code, status)
                self.assertEqual(len(mail.outbox), 0)

    def test_essays_keep_local_content_and_stop_bdr_requests(self) -> None:
        """
        Checks that every essay remains listed after the first failed related-work lookup.
        """
        for index in range(3):
            models.Essay.objects.create(slug=f'essay-{index}', title=f'Local essay {index}', pids='123', text='Local text')
        with BdrMock() as remote:
            remote.add('GET', 'https://localhost/api/search/', body=httpx2.ReadTimeout('Unavailable'))
            response = self.client.get(reverse('essays'))
            for index in range(3):
                self.assertContains(response, f'Local essay {index}')
            self.assertContains(response, 'Local text', count=3)
            self.assertContains(response, 'temporarily unavailable', count=1)
            self.assertIn('no-store', response['Cache-Control'])
            self.assertEqual(len(remote.calls), 1)
            self.assertEqual(len(mail.outbox), 0)

    def test_local_detail_pages_survive_outage(self) -> None:
        """
        Checks that essays, shops, and biographies retain local text during a BDR outage.
        """
        models.Essay.objects.create(slug='example', title='Essay title', text='Local essay text', pids='123')
        models.Shop.objects.create(slug='example', title='Shop title', text='Local shop text', pids='123')
        bio = models.Biography.objects.create(name='Local person', bio='Local biography text')
        examples = [
            (reverse('specific_essay', args=['example']), 'Local essay text'),
            (reverse('specific_shop', args=['example']), 'Local shop text'),
            (reverse('person_detail', args=[bio.trp_id]), 'Local biography text'),
        ]
        for route, local_text in examples:
            with self.subTest(route=route), BdrMock() as remote:
                remote.add('GET', 'https://localhost/api/search/', status=503)
                remote.add('GET', f'https://localhost/api/collections/{settings.TTWR_COLLECTION_PID}/', status=503)
                response = self.client.get(route)
                self.assertContains(response, local_text)
                self.assertContains(response, 'temporarily unavailable')
                self.assertEqual(len(remote.calls), 1)
                self.assertEqual(len(mail.outbox), 0)

    def test_annotation_write_failure_sends_no_mail(self) -> None:
        """
        Checks that failed annotation creates and updates are not retried or emailed.
        """
        user = User.objects.create_user('editor', password='test-password')
        self.client.force_login(user)
        data = {
            'title': 'Example annotation',
            'people-TOTAL_FORMS': '0',
            'people-INITIAL_FORMS': '0',
            'inscriptions-TOTAL_FORMS': '0',
            'inscriptions-INITIAL_FORMS': '0',
        }
        routes = [
            (reverse('new_annotation', args=['123', '456']), 'POST'),
            (reverse('new_print_annotation', args=['456']), 'POST'),
            (reverse('edit_annotation', args=['123', '456', '234']), 'PUT'),
            (reverse('edit_print_annotation', args=['456', '234']), 'PUT'),
        ]
        for route, method in routes:
            with self.subTest(route=route), BdrMock() as remote:
                remote.add('GET', 'https://localhost/storage/testsuite:234/MODS/', body=responses_data.SAMPLE_ANNOTATION_XML)
                remote.add(method, 'https://localhost/api/items/v1/', body=httpx2.ReadTimeout('Unavailable'))
                response = self.client.post(route, data)
                self.assertContains(response, 'could not confirm whether your annotation was saved', status_code=503)
                self.assertEqual(len([call for call in remote.calls if call.method == method]), 1)
                self.assertEqual(len(mail.outbox), 0)

    @override_settings(BDR_CONNECT_TIMEOUT=1.5, BDR_READ_TIMEOUT=3.5)
    def test_search_has_configured_timeout_and_notice(self) -> None:
        """
        Checks that browser search receives a timeout and an accessible outage notice.
        """
        response = self.client.get(reverse('search_page'))
        self.assertContains(response, 'timeout: 5000')
        self.assertContains(response, 'role="status"')
        self.assertContains(response, 'Our monitoring service alerts staff')
        with override_settings(BDR_CONNECT_TIMEOUT=0.0001, BDR_READ_TIMEOUT=0.0001):
            response = self.client.get(reverse('search_page'))
            self.assertContains(response, 'timeout: 1')


class TestBdrEmailFilter(SimpleTestCase):
    def test_filter_only_skips_handled_outage_responses(self) -> None:
        """
        Checks that other 503s, 500s, security errors, and tracebacks still reach email.
        """
        request = RequestFactory().get('/books/')
        record = logging.makeLogRecord({'name': 'django.request', 'status_code': 503, 'request': request})
        email_filter = SkipHandledBdrFailure()
        self.assertTrue(email_filter.filter(record))
        request.META['rome.bdr_unavailable_response'] = True
        self.assertFalse(email_filter.filter(record))
        record.status_code = 500
        self.assertTrue(email_filter.filter(record))
        record.status_code = 503
        record.name = 'django.security'
        self.assertTrue(email_filter.filter(record))
        record.name = 'django.request'
        record.exc_info = (ValueError, ValueError('Unexpected'), None)
        self.assertTrue(email_filter.filter(record))
