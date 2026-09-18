from django.contrib.auth.models import User
from django.http import HttpResponseBase
from django.test import Client, TestCase
from django.urls import reverse


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
