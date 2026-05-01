import json
import logging
from pathlib import Path
import re

import responses
from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from rome_app import models, views

from . import responses_data

log = logging.getLogger(__name__)


def _relative_luminance(color: str) -> float:
    """
    Calculate the WCAG relative luminance for a hex color.

    Called by: unit_tests.test_views._contrast_ratio()
    """
    normalized_color = color
    if len(color) == 4:
        normalized_color = '#' + ''.join(channel * 2 for channel in color[1:])

    channels: list[float] = [int(normalized_color[index : index + 2], 16) / 255 for index in range(1, 7, 2)]
    adjusted_channels: list[float] = []
    for channel in channels:
        adjusted_channels.append(channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4)
    red, green, blue = adjusted_channels
    return (0.2126 * red) + (0.7152 * green) + (0.0722 * blue)


def _contrast_ratio(foreground: str, background: str) -> float:
    """
    Calculate the WCAG contrast ratio between two hex colors.

    Called by: unit_tests.test_views.TestStaticViews.test_accessible_contrast_styles()
    """
    luminance_a = _relative_luminance(foreground)
    luminance_b = _relative_luminance(background)
    lighter = max(luminance_a, luminance_b)
    darker = min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def _css_property_value(css: str, selector: str, property_name: str) -> str:
    """
    Extract a CSS property value from a selector block.

    Called by: unit_tests.test_views.TestStaticViews.test_accessible_contrast_styles()
    """
    block_match = re.search(rf'{re.escape(selector)}\s*\{{(?P<body>.*?)\}}', css, re.DOTALL)
    if not block_match:
        msg = f'Could not find CSS selector: {selector}'
        raise AssertionError(msg)

    property_match = re.search(rf'{re.escape(property_name)}\s*:\s*(?P<value>[^;]+);', block_match.group('body'))
    if not property_match:
        msg = f'Could not find property {property_name} in selector {selector}'
        raise AssertionError(msg)
    return property_match.group('value').strip()


def _first_hex_color(value: str) -> str:
    """
    Extract the first hex color token from a CSS property value.

    Called by: unit_tests.test_views.TestStaticViews.test_accessible_contrast_styles()
    """
    color_match = re.search(r'#[0-9a-fA-F]{6}', value)
    if not color_match:
        msg = f'Could not find a hex color in value: {value}'
        raise AssertionError(msg)
    return color_match.group(0)


def get_auth_client(superuser=False):
    username = 'someone@brown.edu'
    password = 'pw'
    u = User.objects.create_user(username, password=password)
    if superuser:
        u.is_staff = True
        u.is_superuser = True
        u.save()
    auth_client = Client()
    logged_in = auth_client.login(username=username, password=password)
    return auth_client


class TestAdminViews(TestCase):
    def test_auth(self):
        url = reverse('admin:rome_app_biography_changelist')
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('admin:login'), url))

    def test_list_bios(self):
        url = reverse('admin:rome_app_biography_changelist')
        auth_client = get_auth_client(superuser=True)
        response = auth_client.get(url)
        self.assertContains(response, 'Select biography to change')

    def test_view_bio(self):
        bio = models.Biography.objects.create(name='Someone')
        url = reverse('admin:rome_app_biography_change', args=(bio.id,))
        auth_client = get_auth_client(superuser=True)
        response = auth_client.get(url)
        self.assertContains(response, 'Change biography')


class TestStaticViews(TestCase):
    def test_accessible_contrast_styles(self):
        """
        Checks that the shared contrast fix uses colors that satisfy WCAG contrast thresholds.
        """
        common_css = Path(settings.BASE_DIR, 'rome_app/static/rome/css/common.css').read_text()
        content_css = Path(settings.BASE_DIR, 'rome_app/static/rome/css/content.css').read_text()
        body_link_color = _css_property_value(common_css, 'a', 'color')
        breadcrumb_background = _first_hex_color(_css_property_value(common_css, '#page_head .breadcrumb-nav', 'background'))
        breadcrumb_link_color = _css_property_value(common_css, '.breadcrumb-nav a', 'color')
        breadcrumb_separator_color = _css_property_value(common_css, '.breadcrumb-separator', 'color')
        result_link_color = _css_property_value(content_css, '.metadata a', 'color')

        self.assertGreaterEqual(_contrast_ratio(body_link_color, '#E8C577'), 4.5)
        self.assertGreaterEqual(_contrast_ratio(result_link_color, '#F2D69E'), 4.5)
        self.assertGreaterEqual(_contrast_ratio(breadcrumb_link_color, breadcrumb_background), 4.5)
        self.assertGreaterEqual(_contrast_ratio(breadcrumb_separator_color, breadcrumb_background), 4.5)

    def test_accessible_non_link_contrast_styles(self):
        """
        Checks that non-link text colors pass WCAG AA contrast against the info-box and page-head backgrounds.
        """
        common_css = Path(settings.BASE_DIR, 'rome_app/static/rome/css/common.css').read_text()
        content_css = Path(settings.BASE_DIR, 'rome_app/static/rome/css/content.css').read_text()
        home_css = Path(settings.BASE_DIR, 'rome_app/static/rome/css/home.css').read_text()
        links_css = Path(settings.BASE_DIR, 'rome_app/static/rome/css/links.css').read_text()

        ## info-box beige (#F2D69E) and page-head pale yellow (#F9EDD2) backgrounds
        page_body_li_color = _css_property_value(links_css, '#page_body li', 'color')
        page_head_li_color = _css_property_value(content_css, '#page_head li', 'color')
        annot_field_label_color = _css_property_value(content_css, '#metadata .annot_field b', 'color')
        extra_text_color = _css_property_value(content_css, '.metadata div.extra', 'color')
        h2_color = _css_property_value(home_css, 'h2', 'color')
        sitenav_link_color = _css_property_value(home_css, '#sitenav ul li a', 'color')
        field_label_color = _css_property_value(common_css, '.field-label', 'color')
        pagination_btn_color = _css_property_value(common_css, '.pagination_rome > .btn', 'color')

        ## #page_body li must pass against both info-box beige and white
        self.assertGreaterEqual(_contrast_ratio(page_body_li_color, '#F2D69E'), 4.5, '#page_body li vs #F2D69E')
        self.assertGreaterEqual(_contrast_ratio(page_body_li_color, '#FFFFFF'), 4.5, '#page_body li vs white')

        ## #page_head li renders on page-head pale yellow background (#F9EDD2)
        self.assertGreaterEqual(_contrast_ratio(page_head_li_color, '#F9EDD2'), 4.5, '#page_head li vs #F9EDD2')
        self.assertGreaterEqual(_contrast_ratio(page_head_li_color, '#FFFFFF'), 4.5, '#page_head li vs white')

        ## annotation field bold labels appear inside the #F2D69E detail container
        self.assertGreaterEqual(_contrast_ratio(annot_field_label_color, '#F2D69E'), 4.5, '.annot_field b vs #F2D69E')
        self.assertGreaterEqual(_contrast_ratio(annot_field_label_color, '#FFFFFF'), 4.5, '.annot_field b vs white')

        ## extra metadata text appears in the #F2D69E result cards
        self.assertGreaterEqual(_contrast_ratio(extra_text_color, '#F2D69E'), 4.5, '.metadata .extra vs #F2D69E')
        self.assertGreaterEqual(_contrast_ratio(extra_text_color, '#FFFFFF'), 4.5, '.metadata .extra vs white')

        ## h2 on the home page renders on #F9EDD2
        self.assertGreaterEqual(_contrast_ratio(h2_color, '#F9EDD2'), 4.5, 'h2 vs #F9EDD2')
        self.assertGreaterEqual(_contrast_ratio(h2_color, '#FFFFFF'), 4.5, 'h2 vs white')

        ## sitenav links render on #F9EDD2 sitenav list-item background
        self.assertGreaterEqual(_contrast_ratio(sitenav_link_color, '#F9EDD2'), 4.5, 'sitenav a vs #F9EDD2')
        self.assertGreaterEqual(_contrast_ratio(sitenav_link_color, '#FFFFFF'), 4.5, 'sitenav a vs white')

        ## .field-label spans appear inside #F2D69E detail containers
        self.assertGreaterEqual(_contrast_ratio(field_label_color, '#F2D69E'), 4.5, '.field-label vs #F2D69E')
        self.assertGreaterEqual(_contrast_ratio(field_label_color, '#FFFFFF'), 4.5, '.field-label vs white')

        ## pagination buttons appear on a white background
        self.assertGreaterEqual(_contrast_ratio(pagination_btn_color, '#FFFFFF'), 4.5, '.pagination_rome .btn vs white')

    def test_index(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'The Theater that was Rome')

    def test_about(self):
        models.Static.objects.create(title='About', text='### Red Sox lineup[^n1]\n\n[^n1]: footnote text')
        response = self.client.get(reverse('about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h3>Red Sox lineup')  # make sure that basic markdown was rendered
        self.assertContains(response, '<p>footnote text')  # make sure that footnote was rendered
        self.assertContains(response, 'aria-hidden="true" class="breadcrumb-separator"')

    def test_links(self):
        models.Static.objects.create(title='Links', text='### Links')
        response = self.client.get(reverse('links'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h2>Links</h2>')

    def test_shops(self):
        models.Static.objects.create(title='Shops', text='### Shops')
        response = self.client.get(reverse('shops'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Shops')

    def test_search(self):
        # this page is static as far as the django view is concerned
        response = self.client.get(reverse('search_page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rome - Search')

    def test_login_title(self):
        response = self.client.get(reverse('rome_login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<title>Login</title>', html=True)
        self.assertContains(response, '</head>')


class TestBooksViews(TestCase):
    @responses.activate
    def test_book_list_api_error(self):
        responses.add(responses.GET, f'https://localhost/api/collections/{settings.TTWR_COLLECTION_PID}/', status=500)
        url = reverse('books')
        response = self.client.get(url)
        self.assertContains(response, 'error loading list of books', status_code=500)

    @responses.activate
    def test_book_list(self):
        data = {
            'items': {
                'numFound': 1,
                'docs': [
                    {
                        'pid': 'testsuite:1234abcd',
                        'primary_title': 'Title',
                        'uri': 'http://localhost/studio/testsuite:1234abcd/',
                    }
                ],
            },
        }
        responses.add(
            responses.GET,
            f'https://localhost/api/collections/{settings.TTWR_COLLECTION_PID}/',
            body=json.dumps(data),
            status=200,
            content_type='application/json',
        )
        url = reverse('books')
        response = self.client.get(url)
        self.assertContains(response, 'Full Title:')
        self.assertContains(response, 'ID: 1234abcd')

    @responses.activate
    def test_book_not_found(self):
        responses.add(
            responses.GET,
            'https://localhost/api/items/testsuite:123/',
            body='',
            status=404,
        )
        url = reverse('thumbnail_viewer', kwargs={'book_id': '123'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_new_annotation_auth(self):
        url = reverse('new_annotation', kwargs={'book_id': '230605', 'page_id': '230606'})
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('rome_login'), url))

    def test_new_annotation_get(self):
        auth_client = get_auth_client()
        url = reverse('new_annotation', kwargs={'book_id': '230605', 'page_id': '230606'})
        response = auth_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<!DOCTYPE html>')
        self.assertContains(response, '<meta charset="utf-8">', html=True)
        self.assertContains(response, '<title>Create Annotation</title>', html=True)
        self.assertContains(response, 'value="Submit Annotation"')

    @responses.activate
    def test_new_annotation_post(self):
        responses.add(
            responses.POST,
            'https://localhost/api/items/v1/',
            body=json.dumps({'pid': 'testsuite:111111'}),
            status=200,
            content_type='application/json',
        )
        auth_client = get_auth_client()
        url = reverse('new_annotation', kwargs={'book_id': '1234', 'page_id': '5678'})
        data = {
            'title': 'tëst title',
            'people-TOTAL_FORMS': '1',
            'people-INITIAL_FORMS': '0',
            'people-MAX_NUM_FORMS': '',
            'inscriptions-TOTAL_FORMS': '1',
            'inscriptions-INITIAL_FORMS': '0',
            'inscriptions-MAX_NUM_FORMS': '',
        }
        response = auth_client.post(url, data)
        redirect_url = reverse('book_page_viewer', kwargs={'book_id': '1234', 'page_id': '5678'})
        self.assertRedirects(response, redirect_url, fetch_redirect_response=False)

    def test_edit_annotation_auth(self):
        url = reverse('edit_annotation', kwargs={'book_id': '224807', 'page_id': '224895', 'anno_id': '228874'})
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('rome_login'), url))

    def test_get_next_prev_pids(self):
        prev_id, next_id = views._get_prev_next_ids({'relations': {'hasPart': []}}, None)
        self.assertEqual(prev_id, 'none')
        self.assertEqual(next_id, 'none')
        hasPart_data = [
            {'pid': 'test:111', 'order': '1'},
            {'pid': 'test:112', 'order': '2'},
            {'pid': 'test:113', 'order': '3'},
        ]
        prev_id, next_id = views._get_prev_next_ids({'relations': {'hasPart': hasPart_data}}, 'test:112')
        self.assertEqual(prev_id, '111')
        self.assertEqual(next_id, '113')
        hasPart_data = [
            {'pid': 'test:111', 'order': '1'},
            {'pid': 'test:112', 'order': '1-3'},
            {'pid': 'test:113', 'order': '3'},
        ]
        prev_id, next_id = views._get_prev_next_ids({'relations': {'hasPart': hasPart_data}}, 'test:112')
        self.assertEqual(prev_id, '111')
        self.assertEqual(next_id, '113')


class TestPageViews(TestCase):
    @responses.activate
    def test_page_detail(self):
        responses.add(
            responses.GET,
            'https://localhost/api/items/testsuite:123/',
            body=responses_data.BOOK_ITEM_API_DATA,
            status=200,
            content_type='application/json',
        )
        responses.add(
            responses.GET,
            'https://localhost/api/items/testsuite:123456/',
            body=responses_data.ITEM_API_DATA,
            status=200,
            content_type='application/json',
        )
        responses.add(
            responses.GET,
            'https://localhost/storage/testsuite:234/MODS/',
            body=responses_data.SAMPLE_ANNOTATION_XML,
            status=200,
            content_type='text/xml',
        )
        url = reverse('book_page_viewer', kwargs={'book_id': '123', 'page_id': '123456'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @responses.activate
    def test_page_detail_invalid_annotation(self):
        responses.add(
            responses.GET,
            'https://localhost/api/items/testsuite:123/',
            body=responses_data.BOOK_ITEM_API_DATA,
            status=200,
            content_type='application/json',
        )
        responses.add(
            responses.GET,
            'https://localhost/api/items/testsuite:123456/',
            body=responses_data.ITEM_API_DATA,
            status=200,
            content_type='application/json',
        )
        responses.add(
            responses.GET,
            'https://localhost/storage/testsuite:234/MODS/',
            body=responses_data.INVALID_SAMPLE_ANNOTATION_XML,
            status=200,
            content_type='text/xml',
        )
        url = reverse('book_page_viewer', kwargs={'book_id': '123', 'page_id': '123456'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)


class TestPrintsViews(TestCase):
    @responses.activate
    def test_print_list(self):
        prints_search_url = f'https://localhost/api/search/?q=rel_is_member_of_collection_ssim:"{settings.TTWR_COLLECTION_PID}"+AND+(genre_aat:%22etchings%20(prints)%22+OR+genre_aat:%22engravings%20(prints)%22)&rows=1000'
        responses.add(
            responses.GET,
            prints_search_url,
            body=responses_data.PRINTS,
            status=200,
            content_type='application/json',
            match_querystring=True,
        )
        responses.add(
            responses.GET,
            'https://localhost/api/items/testsuite:123456/',
            body=responses_data.ITEM_API_DATA,
            status=200,
            content_type='application/json',
        )
        url = reverse('prints')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @responses.activate
    def test_print_list_sort_by(self):
        prints_search_url = f'https://localhost/api/search/?q=rel_is_member_of_collection_ssim:"{settings.TTWR_COLLECTION_PID}"+AND+(genre_aat:%22etchings%20(prints)%22+OR+genre_aat:%22engravings%20(prints)%22)&rows=1000'
        responses.add(
            responses.GET,
            prints_search_url,
            body=responses_data.PRINTS,
            status=200,
            content_type='application/json',
            match_querystring=True,
        )
        responses.add(
            responses.GET,
            'https://localhost/api/items/testsuite:123456/',
            body=responses_data.ITEM_API_DATA,
            status=200,
            content_type='application/json',
        )
        url = reverse('prints')
        response = self.client.get(f'{url}?sort_by=authors_abcd')
        self.assertEqual(response.status_code, 200)

    @responses.activate
    def test_print_detail(self):
        responses.add(
            responses.GET,
            'https://localhost/api/items/testsuite:123456/',
            body=responses_data.ITEM_API_DATA,
            status=200,
            content_type='application/json',
        )
        responses.add(
            responses.GET,
            'https://localhost/storage/testsuite:234/MODS/',
            body=responses_data.SAMPLE_ANNOTATION_XML,
            status=200,
            content_type='text/xml',
        )
        url = reverse('specific_print', kwargs={'print_id': '123456'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_new_print_annotation_auth(self):
        url = reverse('new_print_annotation', kwargs={'print_id': '230631'})
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('rome_login'), url))

    def test_new_print_annotation_get(self):
        auth_client = get_auth_client()
        url = reverse('new_print_annotation', kwargs={'print_id': '230631'})
        response = auth_client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'value="Submit Annotation"')

    def test_edit_print_annotation_auth(self):
        url = reverse('edit_print_annotation', kwargs={'print_id': '230631', 'anno_id': '230632'})
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('rome_login'), url))

    @responses.activate
    def test_edit_print_annotation_get(self):
        models.Biography.objects.create(name='Someone', trp_id='0260')
        models.Role.objects.create(text='author')
        models.Genre.objects.create(text='book')
        responses.add(
            responses.GET,
            'https://localhost/storage/testsuite:2/MODS/',
            body=responses_data.SAMPLE_ANNOTATION_XML,
            status=200,
            content_type='text/xml',
        )
        auth_client = get_auth_client()
        url = reverse('edit_print_annotation', kwargs={'print_id': '1', 'anno_id': '2'})
        response = auth_client.get(url)
        self.assertEqual(response.status_code, 200, f'{response.status_code} - {response.content.decode("utf8")}')
        self.assertContains(response, 'value="Submit Annotation"')

    @responses.activate
    def test_edit_print_annotation_get_error(self):
        responses.add(
            responses.GET,
            'https://localhost/storage/testsuite:2/MODS/',
            body=responses_data.INVALID_SAMPLE_ANNOTATION_XML,
            status=200,
            content_type='text/xml',
        )
        auth_client = get_auth_client()
        url = reverse('edit_print_annotation', kwargs={'print_id': '1', 'anno_id': '2'})
        response = auth_client.get(url)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, '[Django] TTWR create/edit annotation error')
        self.assertTrue('no person with trp_id' in mail.outbox[0].body)


class TestEssaysViews(TestCase):
    def test_essays(self):
        response = self.client.get(reverse('essays'))
        self.assertEqual(response.status_code, 200)
        models.Essay.objects.create(slug='ger', author='David Ortiz', title='Rëd Sox')
        response = self.client.get(reverse('essays'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rëd Sox')

    @responses.activate
    def test_specific_essay(self):
        responses.add(
            responses.GET,
            'https://localhost/api/search/',
            body=json.dumps({'response': {'docs': [{'pid': 'testsuite:230605', 'primary_title': 'book'}]}}),
            status=200,
            content_type='application/json',
        )
        models.Essay.objects.create(
            slug='ger',
            author='David Ortiz',
            title='Rëd Sox',
            text='### Red Sox lineup[^n1]\n\n[^n1]: footnote text',
            pids='230605',
        )
        response = self.client.get(reverse('specific_essay', kwargs={'essay_slug': 'ger'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h3>Red Sox lineup')  # make sure that basic markdown was rendered
        self.assertContains(response, '<p>footnote text')  # make sure that footnote was rendered
        self.assertContains(response, '230605')  # make sure that the related pid appeared in the menu


class TestPeopleViews(TransactionTestCase):
    def test_people(self):
        models.Biography.objects.create(name='Frëd', trp_id='0001')
        response = self.client.get(reverse('people'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Frëd')

    @responses.activate
    def test_person(self):
        base_url = f'https://localhost/api/collections/{settings.TTWR_COLLECTION_PID}/'
        params = (
            'q=genre_aat:books+AND+name:%22Fr%C3%ABd%22&fq=object_type:implicit-set&fl=*&fq=discover:BDR_PUBLIC&rows=6000'
        )
        responses.add(
            responses.GET,
            '%s?%s' % (base_url, params),
            body=responses_data.BIO_BOOKS,
            status=200,
            content_type='application/json',
            match_querystring=True,
        )
        prints_params = 'q=(genre_aat:%22etchings%20(prints)%22+OR+genre_aat:%22engravings%20(prints)%22)+AND+name:%22Fr%C3%ABd%22&fq=object_type:implicit-set&fl=*&fq=discover:BDR_PUBLIC&rows=6000'
        responses.add(
            responses.GET,
            '%s?%s' % (base_url, prints_params),
            body=responses_data.BIO_PRINTS,
            status=200,
            content_type='application/json',
            match_querystring=True,
        )
        anno_search_url = f'https://localhost/api/search/?q=rel_is_member_of_collection_ssim:"{settings.TTWR_COLLECTION_PID}"+AND+object_type:%22annotation%22+AND+contributor:%22Fr%C3%ABd%22+AND+display:BDR_PUBLIC&rows=6000&fl=rel_is_annotation_of_ssim,primary_title,pid,nonsort'
        responses.add(
            responses.GET,
            anno_search_url,
            body=responses_data.ANNOTATIONS,
            status=200,
            content_type='application/json',
            match_querystring=True,
        )
        pages_search_url = 'https://localhost/api/search/?q=(pid:test%5C:1234)+AND+display:BDR_PUBLIC&fl=pid,primary_title,nonsort,object_type,rel_is_part_of_ssim,rel_has_pagination_ssim&rows=50'
        responses.add(
            responses.GET,
            pages_search_url,
            body=responses_data.PAGES,
            status=200,
            content_type='application/json',
            match_querystring=True,
        )
        models.Biography.objects.create(name='Frëd', trp_id='0001')
        response = self.client.get(reverse('person_detail', kwargs={'trp_id': '0001'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Frëd')


class TestShopsViews(TransactionTestCase):
    def test_shop_list(self):
        models.Shop.objects.create(title='Store', slug='store', text='foo')
        response = self.client.get(reverse('shop_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'foo')

    @responses.activate
    def test_shop(self):
        responses.add(
            responses.GET,
            'https://localhost/api/search/',
            body=json.dumps({'response': {'docs': [{'pid': 'testsuite:230605', 'primary_title': 'book'}]}}),
            status=200,
            content_type='application/json',
        )
        models.Shop.objects.create(
            title='Store', slug='store', text='### Red Sox lineup[^n1]\n\n[^n1]: footnote text', pids='230605'
        )
        response = self.client.get(reverse('specific_shop', kwargs={'shop_slug': 'store'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h3>Red Sox lineup')  # make sure that basic markdown was rendered
        self.assertContains(response, '<p>footnote text')  # make sure that footnote was rendered
        self.assertContains(response, '230605')  # make sure that the related pid appeared in the menu

    def test_shop_url(self):
        url = reverse('specific_shop', kwargs={'shop_slug': 'abc-def'})


class TestDocumentViews(TransactionTestCase):
    def test_documents(self):
        response = self.client.get(reverse('documents'))
        self.assertEqual(response.status_code, 200)

    def test_specific_document(self):
        models.Document.objects.create(
            slug='ger', consagra='0', title='Rëd Sox', text='### Red Sox lineup[^n1]\n\n[^n1]: footnote text'
        )
        response = self.client.get(reverse('specific_document', kwargs={'document_slug': 'ger'}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<h3>Red Sox lineup')  # make sure that basic markdown was rendered
        self.assertContains(response, '<p>footnote text')  # make sure that footnote was rendered


class TestRecordCreatorViews(TestCase):
    def setUp(self):
        """
        Note: clears data, but does not reset sequences, so don't rely on primary-key values.
        """
        models.Genre.objects.all().delete()
        models.Role.objects.all().delete()
        models.Biography.objects.all().delete()

    def test_new_genre_auth(self):
        url = reverse('new_genre')
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('rome_login'), url))

    def test_new_genre(self):
        auth_client = get_auth_client()
        response = auth_client.get(reverse('new_genre'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<!DOCTYPE html>')
        self.assertContains(response, '<meta charset="utf-8">', html=True)
        self.assertContains(response, '<title>Create Record</title>', html=True)
        self.assertContains(response, 'Text')

    def test_new_genre_post(self):
        auth_client = get_auth_client()
        self.assertEqual(len(models.Genre.objects.all()), 0)
        response = auth_client.post(reverse('new_genre'), {'text': 'Book'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<title>Record Created</title>', html=True)
        new_genre = models.Genre.objects.get(text='Book')
        expected_js = f'opener.dismissAddAnotherPopup(window, "{new_genre.pk}", "Book");'
        self.assertContains(response, expected_js)
        self.assertEqual(len(models.Genre.objects.all()), 1)
        self.assertEqual(models.Genre.objects.all()[0].text, 'Book')

    def test_new_role_auth(self):
        url = reverse('new_role')
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('rome_login'), url))

    def test_new_role(self):
        auth_client = get_auth_client()
        response = auth_client.get(reverse('new_role'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Text')

    def test_new_role_post(self):
        auth_client = get_auth_client()
        self.assertEqual(len(models.Role.objects.all()), 0)
        response = auth_client.post(reverse('new_role'), {'text': 'Auth©r'})
        log.debug(f'response: {response}')
        # print(f'response: {response}')
        # print(f'response.content: {response.content}')
        self.assertEqual(response.status_code, 200)
        new_role = models.Role.objects.get(text='Auth©r')
        expected_js = f'opener.dismissAddAnotherPopup(window, "{new_role.pk}", "Auth©r");'
        self.assertContains(response, expected_js)
        self.assertEqual(len(models.Role.objects.all()), 1)
        self.assertEqual(models.Role.objects.all()[0].text, 'Auth©r')

    def test_new_biography_auth(self):
        url = reverse('new_biography')
        response = self.client.get(url)
        self.assertRedirects(response, '%s?next=%s' % (reverse('rome_login'), url))

    def test_new_biography(self):
        auth_client = get_auth_client()
        response = auth_client.get(reverse('new_biography'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Name')

    def test_new_biography_post(self):
        models.Biography.objects.create(name='Tom', trp_id='0001')
        auth_client = get_auth_client()
        self.assertEqual(len(models.Biography.objects.all()), 1)
        response = auth_client.post(reverse('new_biography'), {'name': 'Säm', 'trp_id': '1'})
        self.assertEqual(response.status_code, 200)
        new_biography = models.Biography.objects.get(name='Säm')
        expected_js = f'opener.dismissAddAnotherPopup(window, "{new_biography.pk}", "Säm (0002)");'
        self.assertContains(response, expected_js)
        self.assertEqual(len(models.Biography.objects.all()), 2)
        self.assertEqual(models.Biography.objects.all()[0].name, 'Säm')


class TestUtilityFunctions(TestCase):
    def test_firstword_content(self):
        self.assertEqual(views.first_word('title sentence here'), 'title')
        self.assertEqual(views.first_word('title'), 'title')

    def test_firstword_nulls(self):
        self.assertEqual('', views.first_word(''))
        self.assertEqual('', views.first_word(None))

    def test_annotation_order(self):
        a = {'orig_title': '1: Italian Words'}
        b = {'orig_title': '2: French Words'}
        c = {'title': '3: English Words'}

        l = sorted([b, c, a], key=lambda an: views.annotation_order(an))

        self.assertDictEqual(l[0], a, 'wrong annotation order')
        self.assertDictEqual(l[1], b, 'wrong annotation order')
        self.assertDictEqual(l[2], c, 'wrong annotation order')
