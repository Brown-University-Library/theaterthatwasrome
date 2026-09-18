from django.contrib.auth.models import User
from django.http.response import HttpResponseBase
from django.test import Client, TestCase
from django.urls import get_script_prefix, reverse, set_script_prefix

from rome_app.lib.login_helpers import editing_destination


class TestWebsiteLogin(TestCase):
    def setUp(self) -> None:
        """
        Creates a website editor without admin access.
        Called by: django.test.TestCase
        """
        self.user = User.objects.create_user(username='website-editor', password='test-password', first_name='Ada')
        self.login_url = reverse('rome_login')

    def test_login_page_assets(self) -> None:
        """
        Checks that the login form has the landing page styles and working image paths.
        """
        response = self.client.get(self.login_url)
        self.assertContains(response, 'rome/css/common.css')
        self.assertContains(response, 'rome/css/home.css')
        self.assertContains(response, 'rome/css/login.css')
        self.assertContains(response, 'rome/images/brown-logo.gif')
        self.assertContains(response, 'rome/images/stg-logo.gif')
        self.assertContains(response, '<h2>Login</h2>', html=True)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertNotContains(response, 'Editing options')
        self.assertNotContains(response, 'Sign out')

    def test_successful_login_stays_on_login_page(self) -> None:
        """
        Checks that a non-staff user sees a welcome message and remains excluded from the admin.
        """
        response = self.client.post(
            self.login_url, {'username': self.user.username, 'password': 'test-password'}, follow=True
        )
        self.assertRedirects(response, self.login_url)
        self.assertContains(response, '<h2>Welcome, Ada</h2>', html=True)
        self.assertContains(response, 'You are logged in.')
        self.assertNotContains(response, 'name="password"')
        self.assertContains(response, 'You can create and edit annotations on book pages and prints.')
        self.assertContains(response, f'<a href="{reverse("books")}">Browse books</a>', html=True)
        self.assertContains(response, f'<a href="{reverse("prints")}">Browse prints</a>', html=True)
        self.assertContains(response, 'Sign out')
        self.assertNotContains(response, 'Open admin')
        self.assertNotContains(response, 'Continue editing')
        self.assertEqual(self.client.session['_auth_user_id'], str(self.user.pk))
        admin_response = self.client.get(reverse('admin:index'))
        assert isinstance(admin_response, HttpResponseBase)
        self.assertEqual(admin_response.status_code, 302)
        self.assertContains(self.client.get(self.login_url), 'Welcome, Ada')

    def test_next_does_not_bypass_welcome_page(self) -> None:
        """
        Checks that both query and submitted return destinations still lead to the welcome page.
        """
        for destination in [reverse('new_genre'), 'https://example.com/']:
            for location in ['query', 'form']:
                with self.subTest(destination=destination, location=location):
                    client = Client()
                    data = {'username': self.user.username, 'password': 'test-password'}
                    url = self.login_url
                    if location == 'query':
                        url = f'{url}?next={destination}'
                    else:
                        data['next'] = destination
                    response = client.post(url, data)
                    self.assertRedirects(response, self.login_url)

    def test_welcome_falls_back_to_username(self) -> None:
        """
        Checks that users without a first name receive a useful welcome message.
        """
        self.user.first_name = ''
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get(self.login_url)
        self.assertContains(response, '<h2>Welcome, website-editor</h2>', html=True)

    def test_staff_admin_link(self) -> None:
        """
        Checks that staff users see the administration link without needing superuser status.
        """
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get(self.login_url)
        self.assertContains(response, f'<a href="{reverse("admin:index")}">Open admin</a>', html=True)

    def test_continue_editing_after_login(self) -> None:
        """
        Checks that editing destinations survive the login form and appear as optional links after login.
        """
        destinations = [
            reverse('new_annotation', kwargs={'book_id': '123', 'page_id': '456'}),
            reverse('edit_annotation', kwargs={'book_id': '123', 'page_id': '456', 'anno_id': '789'}),
            reverse('new_print_annotation', kwargs={'print_id': '123'}),
            reverse('edit_print_annotation', kwargs={'print_id': '123', 'anno_id': '789'}) + '?page=2&sort=title',
        ]
        for destination in destinations:
            with self.subTest(destination=destination):
                client = Client()
                response = client.get(destination, follow=True)
                self.assertContains(response, f'<input type="hidden" name="next" value="{destination}">', html=True)
                data = {'username': self.user.username, 'password': 'test-password', 'next': destination}
                response = client.post(self.login_url, data, follow=True)
                self.assertRedirects(response, self.login_url)
                self.assertContains(response, f'<a href="{destination}">Continue editing</a>', html=True)
                self.assertContains(response, 'Welcome, Ada')
                self.assertContains(client.get(self.login_url), 'Continue editing')

    def test_failed_login_preserves_editing_destination(self) -> None:
        """
        Checks that a failed login keeps the return destination available for the next attempt.
        """
        destination = reverse('new_print_annotation', kwargs={'print_id': '123'})
        response = self.client.post(
            self.login_url, {'username': self.user.username, 'password': 'wrong-password', 'next': destination}
        )
        self.assertContains(response, 'role="alert"')
        self.assertContains(response, f'<input type="hidden" name="next" value="{destination}">', html=True)

    def test_continue_editing_rejects_other_destinations(self) -> None:
        """
        Checks that return links cannot lead outside the website or to unrelated routes.
        """
        destinations = [
            'https://example.com/',
            '//example.com/',
            '/\\example.com/',
            'javascript:alert(1)',
            reverse('admin:index'),
            reverse('rome_login'),
            reverse('rome_logout'),
            reverse('books'),
            '/missing/',
        ]
        for destination in destinations:
            with self.subTest(destination=destination):
                response = self.client.get(self.login_url, {'next': destination})
                self.assertNotContains(response, 'name="next"')
        self.client.force_login(self.user)
        for destination in destinations:
            with self.subTest(destination=destination):
                response = self.client.get(self.login_url, {'next': destination})
                self.assertNotContains(response, 'Continue editing')

    def test_continue_editing_with_url_prefix(self) -> None:
        """
        Checks that return destinations work when the website is mounted under a URL prefix.
        """
        previous_prefix = get_script_prefix()
        try:
            set_script_prefix('/rome/')
            destination = reverse('new_annotation', kwargs={'book_id': '123', 'page_id': '456'})
            self.assertEqual(editing_destination(destination), destination)
            self.assertEqual(editing_destination('/somewhere-else' + destination), '')
        finally:
            set_script_prefix(previous_prefix)

    def test_sign_out(self) -> None:
        """
        Checks that signing out clears authentication and the return link and restores the login form.
        """
        self.client.force_login(self.user)
        session = self.client.session
        session['rome_login_continue'] = reverse('new_genre')
        session.save()
        response = self.client.post(reverse('rome_logout'), follow=True)
        self.assertRedirects(response, self.login_url)
        self.assertContains(response, '<h2>Login</h2>', html=True)
        self.assertContains(response, 'name="password"')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertNotIn('rome_login_continue', self.client.session)
        response = self.client.get(reverse('new_genre'))
        self.assertEqual(response.status_code, 302)

    def test_sign_out_requires_post_and_csrf(self) -> None:
        """
        Checks that GET requests and submissions without a CSRF token cannot sign the user out.
        """
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        logout_url = reverse('rome_logout')
        self.assertEqual(client.get(logout_url).status_code, 405)
        self.assertEqual(client.post(logout_url).status_code, 403)
        self.assertEqual(client.session['_auth_user_id'], str(self.user.pk))
        client.get(self.login_url)
        token = client.cookies['csrftoken'].value
        response = client.post(logout_url, {'csrfmiddlewaretoken': token})
        assert isinstance(response, HttpResponseBase)
        self.assertRedirects(response, self.login_url)
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertNotIn('_auth_user_id', client.session)

    def test_welcome_escapes_name(self) -> None:
        """
        Checks that names are displayed as text rather than interpreted as HTML.
        """
        self.user.first_name = '<b>Ada</b>'
        self.user.save()
        self.client.force_login(self.user)
        response = self.client.get(self.login_url)
        self.assertContains(response, 'Welcome, &lt;b&gt;Ada&lt;/b&gt;')
        self.assertNotContains(response, 'Welcome, <b>Ada</b>')

    def test_rejected_login_keeps_form(self) -> None:
        """
        Checks that invalid credentials and inactive accounts cannot reach the welcome state.
        """
        for active, password in [(True, 'wrong-password'), (False, 'test-password')]:
            with self.subTest(active=active):
                self.user.is_active = active
                self.user.save()
                response = self.client.post(self.login_url, {'username': self.user.username, 'password': password})
                self.assertContains(response, 'role="alert"')
                self.assertContains(response, 'name="password"')
                self.assertNotContains(response, 'Welcome,')
                self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_requires_csrf_token(self) -> None:
        """
        Checks that login cannot be submitted without a CSRF token.
        """
        client = Client(enforce_csrf_checks=True)
        response = client.post(self.login_url, {'username': self.user.username, 'password': 'test-password'})
        assert isinstance(response, HttpResponseBase)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('_auth_user_id', client.session)

    def test_login_responses_are_not_cached(self) -> None:
        """
        Checks that login forms, failed logins, redirects, and welcome pages are not cached.
        """
        responses = [
            self.client.get(self.login_url),
            self.client.post(self.login_url, {'username': self.user.username, 'password': 'wrong-password'}),
            self.client.post(self.login_url, {'username': self.user.username, 'password': 'test-password'}),
            self.client.get(self.login_url),
        ]
        for response in responses:
            assert isinstance(response, HttpResponseBase)
            self.assertIn('no-store', response.headers['Cache-Control'])
            self.assertIn('private', response.headers['Cache-Control'])

    def test_credentials_in_get_request_do_not_log_in(self) -> None:
        """
        Checks that credentials must be submitted through the login form.
        """
        response = self.client.get(self.login_url, {'username': self.user.username, 'password': 'test-password'})
        self.assertContains(response, 'name="password"')
        self.assertNotIn('_auth_user_id', self.client.session)
