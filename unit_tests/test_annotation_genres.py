from xml.sax.saxutils import escape

from bdrxml import mods
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from eulxml.xmlmap import load_xmlobject_from_string

from rome_app.models import Annotation, Genre, MissingGenreError
from unit_tests.http_mock import BdrMock


def annotation_xml(genre_text: str | None) -> str:
    """
    Supplies a small annotation with an optional genre.
    Called by: TestAnnotationGenres test methods
    """
    genre_xml = ''
    if genre_text is not None:
        genre_xml = f'<genre authority="aat">{escape(genre_text)}</genre>'
    return (
        '<mods xmlns="http://www.loc.gov/mods/v3">'
        '<titleInfo><title>Example annotation</title></titleInfo>'
        f'{genre_xml}</mods>'
    )


class TestAnnotationGenres(TestCase):
    def setUp(self) -> None:
        """
        Creates an ordinary editor and both annotation edit routes.
        Called by: Django test runner
        """
        user = User.objects.create_user('editor')
        self.client.force_login(user)
        self.routes = [
            (
                reverse('edit_annotation', args=['123', '456', '234']),
                reverse('book_page_viewer', args=['123', '456']),
            ),
            (reverse('edit_print_annotation', args=['456', '234']), reverse('specific_print', args=['456'])),
        ]

    def test_missing_genre_explains_correction_without_writes(self) -> None:
        """
        Checks both edit pages explain the missing genre without changing any records.
        """
        for route, annotation_url in self.routes:
            with self.subTest(route=route), BdrMock() as remote:
                remote.add('GET', 'https://localhost/storage/testsuite:234/MODS/', body=annotation_xml('example genre'))
                response = self.client.get(route)
                self.assertContains(response, 'Annotation needs a genre correction', status_code=409)
                self.assertContains(response, '<strong>example genre</strong>', html=True, status_code=409)
                self.assertContains(response, 'Contact the site editor responsible for genre data.', status_code=409)
                self.assertContains(response, 'The annotation has not been changed.', status_code=409)
                self.assertContains(response, f'href="{annotation_url}"', status_code=409)
                self.assertNotContains(response, '<form', status_code=409)
                self.assertIn('no-store', response['Cache-Control'])
                self.assertEqual([call.method for call in remote.calls], ['GET'])
                self.assertFalse(Genre.objects.exists())
                self.assertEqual(len(mail.outbox), 0)

    def test_matching_genre_loads_selected_choice(self) -> None:
        """
        Checks both forms open with the existing genre selected for an ordinary editor.
        """
        genre = Genre.objects.create(text='example genre')
        for route, _ in self.routes:
            with self.subTest(route=route), BdrMock() as remote:
                remote.add('GET', 'https://localhost/storage/testsuite:234/MODS/', body=annotation_xml(genre.text))
                response = self.client.get(route)
                self.assertContains(response, f'<option value="{genre.id}" selected>example genre</option>', html=True)
                self.assertContains(response, 'value="Submit Annotation"')
                self.assertEqual(Genre.objects.count(), 1)
                self.assertEqual([call.method for call in remote.calls], ['GET'])

    def test_editing_recovers_after_genre_is_added(self) -> None:
        """
        Checks reopening either edit page succeeds after another editor supplies the genre.
        """
        for route, _ in self.routes:
            with self.subTest(route=route), BdrMock() as remote:
                Genre.objects.all().delete()
                remote.add('GET', 'https://localhost/storage/testsuite:234/MODS/', body=annotation_xml('example genre'))
                self.assertEqual(self.client.get(route).status_code, 409)
                Genre.objects.create(text='example genre')
                response = self.client.get(route)
                self.assertContains(response, 'value="Submit Annotation"')
                self.assertEqual([call.method for call in remote.calls], ['GET', 'GET'])

    def test_absent_or_empty_genre_remains_optional(self) -> None:
        """
        Checks both forms still open when the annotation has no genre value.
        """
        for route, _ in self.routes:
            for genre_text in [None, '']:
                with self.subTest(route=route, genre_text=genre_text), BdrMock() as remote:
                    remote.add('GET', 'https://localhost/storage/testsuite:234/MODS/', body=annotation_xml(genre_text))
                    response = self.client.get(route)
                    self.assertContains(response, 'value="Submit Annotation"')
                    self.assertFalse(Genre.objects.exists())
                    self.assertEqual([call.method for call in remote.calls], ['GET'])

    def test_genre_text_is_displayed_as_text(self) -> None:
        """
        Checks annotation genre text stays literal when displayed on either correction page.
        """
        genre_text = 'Example <unlisted> & other'
        for route, _ in self.routes:
            with self.subTest(route=route), BdrMock() as remote:
                remote.add('GET', 'https://localhost/storage/testsuite:234/MODS/', body=annotation_xml(genre_text))
                response = self.client.get(route)
                self.assertContains(response, 'Example &lt;unlisted&gt; &amp; other', status_code=409)
                self.assertNotContains(response, genre_text, status_code=409)

    def test_missing_genre_does_not_cache_incomplete_form_data(self) -> None:
        """
        Checks repeated form reads report the missing genre until it is supplied, preserving XML.
        """
        mods_obj = load_xmlobject_from_string(annotation_xml('example genre'), mods.Mods)
        annotation = Annotation(mods_obj=mods_obj)
        original_xml = annotation.to_mods_xml()
        for _ in range(2):
            with self.assertRaises(MissingGenreError) as error:
                annotation.get_form_data()
            self.assertEqual(error.exception.genre_text, 'example genre')
            self.assertFalse(Genre.objects.exists())
            self.assertEqual(annotation.to_mods_xml(), original_xml)
        genre = Genre.objects.create(text='example genre')
        self.assertEqual(annotation.get_form_data()['genre'], genre.id)
        self.assertEqual(annotation.to_mods_xml(), original_xml)
