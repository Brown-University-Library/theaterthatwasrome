import json
from unittest.mock import patch

import responses
from django.test import TestCase
from django.urls import reverse

from rome_app import models, views
from . import responses_data


def mock_page_responses(page_data: dict[str, object]) -> None:
    """
    Supplies local responses for a book and its page.
    Called by: TestPageMetadata.test_missing_annotation_metadata(), TestPageMetadata.test_missing_pagination()
    """
    responses.reset()
    responses.add(
        responses.GET,
        'https://localhost/api/items/testsuite:123/',
        body=responses_data.BOOK_ITEM_API_DATA,
        content_type='application/json',
    )
    responses.add(
        responses.GET,
        'https://localhost/api/items/testsuite:123456/',
        body=json.dumps(page_data),
        content_type='application/json',
    )


class TestPageMetadata(TestCase):
    @responses.activate
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

    @responses.activate
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
    @responses.activate
    def test_origin_date_text(self) -> None:
        """
        Checks that an origin date comes from XML text and that the impression date remains available.
        """
        url = 'https://localhost/storage/testsuite:234/MODS/'
        responses.add(
            responses.GET,
            url,
            body=(
                '<mods xmlns="http://www.loc.gov/mods/v3"><originInfo>'
                '<dateIssued>1638</dateIssued><dateOther type="impression">1695</dateOther>'
                '</originInfo></mods>'
            ),
            content_type='text/xml',
        )
        annotation = views.get_annotation_detail({'pid': 'testsuite:234', 'xml_uri': url})
        self.assertEqual(annotation['origin'], '1638')
        self.assertEqual(annotation['has_elements']['origin'], 1)
        self.assertEqual(annotation['impression'], '1695')

    @responses.activate
    def test_empty_origin(self) -> None:
        """
        Checks that empty origin metadata does not show a blank origin field.
        """
        url = 'https://localhost/storage/testsuite:234/MODS/'
        for origin_xml in ['<originInfo/>', '<originInfo><dateIssued/></originInfo>']:
            with self.subTest(origin_xml=origin_xml):
                responses.reset()
                responses.add(
                    responses.GET,
                    url,
                    body=f'<mods xmlns="http://www.loc.gov/mods/v3">{origin_xml}</mods>',
                    content_type='text/xml',
                )
                annotation = views.get_annotation_detail({'pid': 'testsuite:234', 'xml_uri': url})
                self.assertEqual(annotation['has_elements']['origin'], 0)
                self.assertNotIn('origin', annotation)


class TestViewResponses(TestCase):
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
