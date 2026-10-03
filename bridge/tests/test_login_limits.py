from contextlib import ExitStack
from datetime import timedelta
from unittest.mock import patch

from axes.handlers.proxy import AxesProxyHandler
from axes.models import AccessAttempt
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone


@override_settings(AXES_FAILURE_LIMIT=5, AXES_COOLOFF_TIME=timedelta(minutes=15))
class LoginLimitTests(TestCase):
    password = 'Test@2026'

    def setUp(self):
        self.user = get_user_model().objects.create_user('teacher', password=self.password)
        self.admin = get_user_model().objects.create_superuser('operator', password=self.password)

    def login(self, username='teacher', password='wrong-password', path='/accounts/login/', client=None, **headers):
        return (client or self.client).post(path, {
            'username': username, 'password': password,
        }, **headers)

    def lock(self, username='teacher', **kwargs):
        for _ in range(4):
            self.assertEqual(self.login(username, **kwargs).status_code, 200)
        response = self.login(username, **kwargs)
        self.assertContains(response, 'Đăng nhập tạm thời bị giới hạn', status_code=429)
        return response

    def clock(self, instant):
        stack = ExitStack()
        stack.enter_context(patch('axes.handlers.proxy.now', return_value=instant))
        stack.enter_context(patch('bridge.security.timezone.now', return_value=instant))
        return stack

    def test_fifth_failure_blocks_correct_password_and_survives_new_handler(self):
        response = self.lock()
        self.assertEqual(response['Retry-After'], '900')
        self.assertEqual(response['Cache-Control'], 'no-store')
        attempt = AccessAttempt.objects.get(username='teacher')
        self.assertEqual(attempt.failures_since_start, 5)
        self.assertNotIn('wrong-password', attempt.post_data)
        AxesProxyHandler.get_implementation(force=True)
        response = self.login(password=self.password, client=Client())
        self.assertEqual(response.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_success_resets_counter_before_limit(self):
        for _ in range(4):
            self.login()
        self.assertEqual(self.login(password=self.password).status_code, 302)
        self.assertFalse(AccessAttempt.objects.filter(username='teacher').exists())
        self.client.post('/accounts/logout/')
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(AccessAttempt.objects.get(username='teacher').failures_since_start, 1)

    def test_web_login_shows_failures_and_remaining_attempts(self):
        response = self.login()
        self.assertContains(response, 'Đã đăng nhập sai 1/5 lần.')
        self.assertContains(response, 'Còn 4 lần thử trước khi tạm khóa.')
        for _ in range(2):
            self.login()
        response = self.login()
        self.assertContains(response, 'Đã đăng nhập sai 4/5 lần.')
        self.assertContains(response, 'Còn 1 lần thử trước khi tạm khóa.')

    def test_admin_and_web_share_counter_and_admin_lockout_page(self):
        for path in ['/accounts/login/', '/admin/login/'] * 2:
            self.assertEqual(self.login('operator', path=path).status_code, 200)
        response = self.login('operator', path='/admin/login/')
        self.assertContains(response, 'href="/admin/login/"', status_code=429)
        self.assertEqual(self.login('operator', self.password).status_code, 429)
        self.assertEqual(self.login('operator', self.password, path='/admin/login/').status_code, 429)

    def test_same_network_other_account_is_not_blocked(self):
        self.lock(REMOTE_ADDR='192.0.2.1')
        self.assertEqual(self.login('operator', self.password, path='/admin/login/', REMOTE_ADDR='192.0.2.1').status_code, 302)

    def test_rotating_network_browser_cookies_and_normalized_username_cannot_bypass(self):
        start = timezone.now()
        for i, username in enumerate(['teacher', ' teacher ', 'ｔｅａｃｈｅｒ', 'teacher', 'teacher']):
            with self.clock(start + timedelta(minutes=i)):
                response = self.login(username, client=Client(), REMOTE_ADDR=f'192.0.2.{i + 1}',
                                      HTTP_USER_AGENT=f'browser-{i}', HTTP_X_FORWARDED_FOR=f'198.51.100.{i + 1}')
            self.assertEqual(response.status_code, 429 if i == 4 else 200)
        self.assertEqual(AccessAttempt.objects.filter(username='teacher').count(), 1)
        # The cooldown starts at the fifth failure, even if earlier browsers' rows
        # would have expired sooner under Axes' default per-browser storage.
        with self.clock(start + timedelta(minutes=15, seconds=1)):
            response = self.login(password=self.password, client=Client(), HTTP_USER_AGENT='another-browser')
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response['Retry-After'], '239')
        with self.clock(start + timedelta(minutes=19, seconds=1)):
            self.assertEqual(self.login(password=self.password, client=Client()).status_code, 302)

    def test_locked_retries_do_not_extend_cooldown(self):
        start = timezone.now()
        with self.clock(start):
            self.lock()
        with self.clock(start + timedelta(minutes=14)):
            response = self.login(password=self.password)
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response['Retry-After'], '60')
            attempt = AccessAttempt.objects.get(username='teacher')
            self.assertEqual(attempt.attempt_time, start)
            self.assertEqual(attempt.failures_since_start, 5)
        with self.clock(start + timedelta(minutes=15, seconds=1)):
            self.assertEqual(self.login(password=self.password).status_code, 302)

    def test_inactivity_expires_failed_counter(self):
        start = timezone.now()
        with self.clock(start):
            for _ in range(4):
                self.login()
        with self.clock(start + timedelta(minutes=15, seconds=1)):
            self.assertEqual(self.login().status_code, 200)
            self.assertEqual(AccessAttempt.objects.get(username='teacher').failures_since_start, 1)

    def test_unknown_username_has_same_lockout_and_invalid_csrf_does_not_count(self):
        secure = Client(enforce_csrf_checks=True)
        self.assertEqual(self.login(client=secure).status_code, 403)
        self.assertFalse(AccessAttempt.objects.exists())
        self.lock('not-an-existing-user')

    def test_admin_can_reset_only_one_account_and_existing_session_can_logout(self):
        logged_in = Client()
        self.login(password=self.password, client=logged_in)
        self.lock()
        self.lock('not-an-existing-user')
        self.assertEqual(logged_in.post('/accounts/logout/').status_code, 302)
        self.assertNotIn('_auth_user_id', logged_in.session)
        call_command('axes_reset_username', 'teacher', verbosity=0)
        self.assertTrue(AccessAttempt.objects.filter(username='not-an-existing-user').exists())
        self.assertEqual(self.login(password=self.password).status_code, 302)
