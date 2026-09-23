from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from lxml.html import fromstring

from rome_app.models import Biography, Genre, Role
from unit_tests.http_mock import BdrMock


class TestAnnotationWidgets(TestCase):
    def setUp(self) -> None:
        """
        Creates an editor for the annotation form checks.
        Called by: Django test runner
        """
        self.client.force_login(User.objects.create_user('editor'))

    def test_create_and_edit_forms_have_labeled_inline_add_controls(self) -> None:
        """
        Checks both annotation types render graphics and preserve popup targets, including new rows.
        """
        routes = [
            reverse('new_annotation', args=['123', '456']),
            reverse('new_print_annotation', args=['456']),
            reverse('edit_annotation', args=['123', '456', '234']),
            reverse('edit_print_annotation', args=['456', '234']),
        ]
        controls = [
            ('genre', 'new_genre', 'Add another genre'),
            ('people-0-person', 'new_biography', 'Add another biography'),
            ('people-0-role', 'new_role', 'Add another role'),
            ('people-__prefix__-person', 'new_biography', 'Add another biography'),
            ('people-__prefix__-role', 'new_role', 'Add another role'),
        ]
        for route in routes:
            with self.subTest(route=route), BdrMock() as remote:
                remote.add(
                    'GET',
                    'https://localhost/storage/testsuite:234/MODS/',
                    body='<mods xmlns="http://www.loc.gov/mods/v3"><titleInfo><title>Example</title></titleInfo></mods>',
                )
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)
                document = fromstring(response.content)
                self.assertEqual(len(document.xpath('//a[@class="add-another"]')), len(controls))
                for name, url_name, label in controls:
                    links = document.xpath('//a[@id=$id]', id=f'add_id_{name}')
                    self.assertEqual(len(links), 1)
                    link = links[0]
                    self.assertEqual(link.get('href'), reverse(url_name))
                    self.assertEqual(link.get('aria-label'), label)
                    self.assertEqual(link.get('title'), label)
                    self.assertEqual(link.get('onclick'), 'return showAddAnotherPopup(this);')
                    self.assertEqual(len(link.xpath('svg[@aria-hidden="true"][@focusable="false"]/path')), 1)
                    self.assertEqual(link.xpath('.//img | .//image | .//use'), [])
                    self.assertEqual(len(document.xpath('//select[@id=$id]', id=f'id_{name}')), 1)

    def test_invalid_submission_keeps_selections_and_add_controls(self) -> None:
        """
        Checks validation errors keep selected values and working links without writing to BDR.
        """
        genre = Genre.objects.create(text='Book')
        person = Biography.objects.create(name='Example author', trp_id='0001')
        role = Role.objects.create(text='author')
        data = {
            'title': '',
            'genre': str(genre.pk),
            'people-TOTAL_FORMS': '1',
            'people-INITIAL_FORMS': '0',
            'people-0-person': str(person.pk),
            'people-0-role': str(role.pk),
            'inscriptions-TOTAL_FORMS': '0',
            'inscriptions-INITIAL_FORMS': '0',
        }
        routes = [
            reverse('new_annotation', args=['123', '456']),
            reverse('new_print_annotation', args=['456']),
        ]
        for route in routes:
            with self.subTest(route=route), BdrMock() as remote:
                response = self.client.post(route, data)
                self.assertContains(response, 'This field is required.')
                document = fromstring(response.content)
                for name, pk in [('genre', genre.pk), ('people-0-person', person.pk), ('people-0-role', role.pk)]:
                    selected = document.xpath('//select[@id=$id]/option[@selected]/@value', id=f'id_{name}')
                    self.assertEqual(selected, [str(pk)])
                    self.assertEqual(len(document.xpath('//a[@id=$id]/svg/path', id=f'add_id_{name}')), 1)
                self.assertEqual(remote.calls, [])
