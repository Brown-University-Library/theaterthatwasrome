import datetime
import json
from unittest.mock import patch

import httpx2
from django.test import RequestFactory, TestCase
from django.urls import reverse

from rome_app import models
from rome_app.lib import annotation_helpers, version_helper

from . import http_mock as bdr_mock
from . import responses_data


def mock_page_responses(page_data: dict[str, object]) -> None:
    """
    Supplies local responses for a book and its page.
    Called by: TestPageMetadata.test_missing_annotation_metadata(), TestPageMetadata.test_missing_pagination()
    """
    bdr_mock.reset()
    bdr_mock.add(
        bdr_mock.GET,
        'https://localhost/api/items/testsuite:123/',
        body=responses_data.BOOK_ITEM_API_DATA,
        content_type='application/json',
    )
    bdr_mock.add(
        bdr_mock.GET,
        'https://localhost/api/items/testsuite:123456/',
        body=json.dumps(page_data),
        content_type='application/json',
    )


class TestPageMetadata(TestCase):
    @bdr_mock.activate
    def test_missing_annotation_metadata(self) -> None:
        """
        Checks that absent or empty annotation metadata still allows a book page to render.
        """
        for relations in [None, {}, {'hasAnnotation': None}, {'hasAnnotation': []}]:
            with self.subTest(relations=relations):
                page_data = json.loads(responses_data.ITEM_API_DATA)
                page_data['relations'] = relations
                mock_page_responses(page_data)
                response = self.client.get(reverse('book_page_viewer', kwargs={'book_id': '123', 'page_id': '123456'}))
                self.assertContains(response, 'Zoomable image viewer: No Title')
                self.assertContains(response, 'Image 1')

        page_data = json.loads(responses_data.ITEM_API_DATA)
        del page_data['relations']
        mock_page_responses(page_data)
        response = self.client.get(reverse('book_page_viewer', kwargs={'book_id': '123', 'page_id': '123456'}))
        self.assertContains(response, 'Image 1')

    @bdr_mock.activate
    def test_missing_pagination(self) -> None:
        """
        Checks that missing page numbers fall back to the page ID and valid numbers are preserved.
        """
        for pagination in [None, [], '', [None], [''], ['7']]:
            with self.subTest(pagination=pagination):
                page_data = json.loads(responses_data.ITEM_API_DATA)
                page_data['relations'] = {'hasAnnotation': []}
                page_data['rel_has_pagination_ssim'] = pagination
                mock_page_responses(page_data)
                response = self.client.get(reverse('book_page_viewer', kwargs={'book_id': '123', 'page_id': '123456'}))
                self.assertContains(response, 'Image 7' if pagination == ['7'] else 'Image 123456')

        del page_data['rel_has_pagination_ssim']
        mock_page_responses(page_data)
        response = self.client.get(reverse('book_page_viewer', kwargs={'book_id': '123', 'page_id': '123456'}))
        self.assertContains(response, 'Image 123456')


class TestAnnotationOrigin(TestCase):
    @bdr_mock.activate
    def test_origin_date_text(self) -> None:
        """
        Checks that an origin date comes from XML text and that the impression date remains available.
        """
        url = 'https://localhost/storage/testsuite:234/MODS/'
        bdr_mock.add(
            bdr_mock.GET,
            url,
            body=(
                '<mods xmlns="http://www.loc.gov/mods/v3"><originInfo>'
                '<dateIssued>1638</dateIssued><dateOther type="impression">1695</dateOther>'
                '</originInfo></mods>'
            ),
            content_type='text/xml',
        )
        annotation = annotation_helpers.get_annotation_detail({'pid': 'testsuite:234', 'xml_uri': url})
        self.assertEqual(annotation['origin'], '1638')
        self.assertEqual(annotation['has_elements']['origin'], 1)
        self.assertEqual(annotation['impression'], '1695')

    @bdr_mock.activate
    def test_empty_origin(self) -> None:
        """
        Checks that empty origin metadata does not show a blank origin field.
        """
        url = 'https://localhost/storage/testsuite:234/MODS/'
        for origin_xml in ['<originInfo/>', '<originInfo><dateIssued/></originInfo>']:
            with self.subTest(origin_xml=origin_xml):
                bdr_mock.reset()
                bdr_mock.add(
                    bdr_mock.GET,
                    url,
                    body=f'<mods xmlns="http://www.loc.gov/mods/v3">{origin_xml}</mods>',
                    content_type='text/xml',
                )
                annotation = annotation_helpers.get_annotation_detail({'pid': 'testsuite:234', 'xml_uri': url})
                self.assertEqual(annotation['has_elements']['origin'], 0)
                self.assertNotIn('origin', annotation)


class TestViewResponses(TestCase):
    def test_people_roles_and_filter(self) -> None:
        """
        Checks that roles display as words and filters match whole roles, including when other people have no roles.
        """
        models.Biography.objects.create(
            name='Sample Artist', roles=' painter ; engraver; ;', birth_date='1600', death_date='1670'
        )
        models.Biography.objects.create(name='Sample Assistant', roles='assistant painter')
        models.Biography.objects.create(name='Sample Unknown', roles=None)
        response = self.client.get(reverse('people'))
        self.assertContains(response, '[painter, engraver]')
        self.assertContains(response, '(1600 to 1670)')
        self.assertContains(response, 'Sample Unknown')
        response = self.client.get(reverse('people'), {'filter': 'painter'})
        self.assertContains(response, 'Sample Artist')
        self.assertNotContains(response, 'Sample Assistant')
        self.assertNotContains(response, 'Sample Unknown')
        self.assertEqual(response.context['num_results'], 1)

    def test_shop_families(self) -> None:
        """
        Checks that shops display their first family and that blank or missing families still render.
        """
        models.Shop.objects.create(
            title='Family Shop',
            slug='family-shop',
            family=' Example Family ; Other Family ;',
            start_date='1600',
            end_date='1670',
        )
        models.Shop.objects.create(title='Unknown Family Shop', slug='unknown-shop', family=None)
        models.Shop.objects.create(title='Blank Family Shop', slug='blank-shop', family=' ; ')
        response = self.client.get(reverse('shop_list'))
        self.assertContains(response, 'Example Family')
        self.assertNotContains(response, 'Other Family')
        self.assertContains(response, 'Unknown Family Shop')
        self.assertContains(response, 'Blank Family Shop')
        self.assertContains(response, '<i>1600</i> — <i>1670</i>', html=True)
        self.assertEqual(response.context['num_results'], 3)

    @bdr_mock.activate
    def test_metadata_request_failures(self) -> None:
        """
        Checks that BDR HTTP errors and timeouts keep the existing page and print error bdr_mock.
        """
        page_url = reverse('book_page_viewer', kwargs={'book_id': '123', 'page_id': '123456'})
        print_url = reverse('specific_print', kwargs={'print_id': '123'})
        for route in [page_url, print_url]:
            for failure in ['Service unavailable', httpx2.ReadTimeout('BDR timed out')]:
                with self.subTest(route=route, failure=type(failure).__name__):
                    bdr_mock.reset()
                    bdr_mock.add(
                        bdr_mock.GET,
                        'https://localhost/api/items/testsuite:123456/',
                        body=responses_data.ITEM_API_DATA,
                        content_type='application/json',
                    )
                    bdr_mock.add(
                        bdr_mock.GET,
                        'https://localhost/api/items/testsuite:123/',
                        body=failure,
                        status=503,
                    )
                    response = self.client.get(route)
                    self.assertEqual(response.status_code, 503)
                    self.assertIn(b'temporarily unavailable', response.content)

    def test_version_timing_with_timezone(self) -> None:
        """
        Checks that version timing accepts a timestamp with a timezone.
        """
        request = RequestFactory().get('/version/')
        started = datetime.datetime.now(tz=datetime.timezone.utc)
        context = version_helper.make_context(request, started, 'example-commit')
        self.assertEqual(context['response']['version'], 'example-commit')
        self.assertRegex(context['response']['timetaken'], r'^\d+:\d{2}:\d{2}')

    def test_role_checker(self) -> None:
        """
        Checks that the role checker returns its result without an undefined logger error.
        """
        response = self.client.get(reverse('temp_roles_checker_url'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['data'], [])
        self.assertEqual(response.json()['__meta__']['bios_with_issues_count'], 0)

    def test_essay_and_note_thumbnail_limit(self) -> None:
        """
        Checks that essays and notes keep their previews and show at most five related page thumbnails.
        """
        essay = models.Essay.objects.create(
            slug='sample-essay', author='Example Author', title='Example Essay', text='A short preview.'
        )
        works = [
            {'pid': f'testsuite:{index}', 'primary_title': f'Page {index}', 'rel_is_part_of_ssim': ['testsuite:100']}
            for index in range(201, 207)
        ]
        works.append({'pid': 'testsuite:300', 'primary_title': 'A standalone print'})
        for is_note in [False, True]:
            with self.subTest(is_note=is_note):
                essay.is_note = is_note
                essay.save()
                with patch.object(models.Essay, 'related_works', return_value=works):
                    response = self.client.get(reverse('essays'))
                self.assertContains(response, 'Example Essay')
                self.assertContains(response, 'A short preview.')
                self.assertContains(response, 'alt="Thumbnail for 100"', count=5)
                self.assertContains(response, '/books/100/201/')
                self.assertNotContains(response, '/books/100/206/')
