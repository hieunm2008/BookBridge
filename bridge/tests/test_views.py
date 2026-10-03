from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from bridge import services
from bridge.models import Audit, Inventory, Loan, Need, Profile, Proposal, School
from .test_services import FixtureMixin


class ViewTests(FixtureMixin, TestCase):
    def setUp(self):
        self.fixture()

    def test_public_and_auth_redirects(self):
        self.assertContains(self.client.get('/'), 'Kết nối sách,')
        self.assertEqual(self.client.get('/dashboard/').status_code, 302)
        self.assertContains(self.client.get('/accounts/login/'), 'Chào mừng trở lại')
        self.assertContains(self.client.post('/accounts/login/', {'username': 'bad', 'password': 'bad'}), 'Tên đăng nhập hoặc mật khẩu không đúng')
        self.assertEqual(self.client.post('/accounts/login/', {'username': 'teacher1', 'password': 'Test@2026', 'next': 'https://evil.example'}).url, '/dashboard/')
        self.assertEqual(self.client.get('/accounts/logout/').status_code, 405)

    def test_every_app_page_renders_with_real_data(self):
        self.client.force_login(self.coord)
        p = services.create_proposal(self.coord)
        loan = services.approve_proposal(self.coord, p.pk)[0]
        paths = ['/dashboard/', '/inventory/', '/inventory/new/', f'/inventory/{self.inv.pk}/edit/', '/requests/', '/requests/new/',
                 f'/requests/{self.n1.pk}/edit/', '/coordination/', f'/coordination/{p.pk}/', '/loans/', f'/loans/{loan.pk}/']
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.assertContains(self.client.get('/dashboard/'), 'Có thể cho mượn')
        self.assertContains(self.client.get('/coordination/'), 'Nhu cầu còn thiếu')

    def test_cross_school_urls_and_post_tampering(self):
        self.client.force_login(self.teachers[3])
        loan = self.approved()[0]
        for path in ['/coordination/', f'/inventory/{self.inv.pk}/edit/', f'/requests/{self.n1.pk}/edit/', f'/loans/{loan.pk}/']:
            self.assertEqual(self.client.get(path).status_code, 403)
        response = self.client.post(f'/inventory/{self.inv.pk}/edit/', {'school': self.schools[3].pk, 'book': self.book.pk, 'owned': 500, 'internal': 0, 'version': 0, 'reason': 'Xâm nhập'})
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(self.client.get('/inventory/'), self.book.title)
        self.assertNotContains(self.client.get('/requests/'), self.schools[1].name)
        self.assertNotContains(self.client.get('/loans/'), loan.code)

    def test_forms_preserve_error_input_and_scoped_school(self):
        self.client.force_login(self.teachers[1])
        data = {'school': self.schools[0].pk, 'book': self.book.pk, 'owned': 7, 'internal': 3, 'reason': ''}
        response = self.client.post('/inventory/new/', data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Inventory.objects.get(school=self.schools[1]).owned, 7)
        inv = Inventory.objects.get(school=self.schools[1])
        response = self.client.post(f'/inventory/{inv.pk}/edit/', {**data, 'owned': 1, 'reason': 'Giảm', 'version': inv.version})
        self.assertContains(response, 'Chưa thể lưu dữ liệu')
        self.assertContains(response, 'value="1"')
        response = self.client.post('/requests/new/', {'book': self.book.pk, 'quantity': 10, 'needed_by': '2026-10-10', 'return_by': '2026-10-01'})
        self.assertContains(response, 'Ngày trả phải bằng hoặc sau ngày cần sách')

    def test_post_actions_and_csrf(self):
        self.client.force_login(self.coord)
        response = self.client.post('/coordination/')
        self.assertEqual(response.status_code, 302)
        p = Proposal.objects.first()
        self.assertEqual(self.client.post(f'/coordination/{p.pk}/', {'action': 'approve'}).status_code, 302)
        self.assertContains(self.client.post(f'/coordination/{p.pk}/', {'action': 'approve'}), 'đã được duyệt')
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.coord)
        self.assertContains(secure.post('/coordination/'), 'Phiên xác nhận đã hết hạn', status_code=403)
        self.assertEqual(self.client.get(f'/requests/{self.n1.pk}/cancel/').status_code, 405)

    def test_dashboard_filters_and_pagination(self):
        self.client.force_login(self.coord)
        self.assertEqual(len(self.client.get('/inventory/?available=1').context['page']), 1)
        self.assertEqual(len(self.client.get('/inventory/?grade=4').context['page']), 0)
        self.assertEqual(len(self.client.get('/requests/?q=Toán&series=A').context['page']), 2)
        self.assertEqual(self.client.get('/inventory/?grade=invalid&page=invalid').status_code, 200)
        self.assertEqual(self.client.get('/coordination/?book=invalid').status_code, 200)
        for i in range(25):
            school = School.objects.create(code=f'P{i}', name=f'P{i}', province='A', locality='X', contact_name='GV')
            Inventory.objects.create(school=school, book=self.book, owned=1)
        response = self.client.get('/inventory/?q=Toán&page=2')
        self.assertEqual(len(response.context['page']), 6)
        self.assertContains(response, 'q=To%C3%A1n')

    def test_unassigned_account_cannot_use_app(self):
        user = get_user_model().objects.create_user('unassigned')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/dashboard/').status_code, 403)

    def test_unassigned_account_can_log_out_from_permission_error(self):
        get_user_model().objects.create_user('unassigned', password='Test@2026')
        secure = Client(enforce_csrf_checks=True)
        secure.get('/accounts/login/')
        response = secure.post('/accounts/login/', {
            'username': 'unassigned', 'password': 'Test@2026',
            'csrfmiddlewaretoken': secure.cookies['csrftoken'].value,
        }, follow=True)
        self.assertContains(response, 'Bạn chưa có quyền truy cập', status_code=403)
        self.assertContains(response, 'action="/accounts/logout/"', status_code=403)
        self.assertContains(response, 'name="next" value="/accounts/login/"', status_code=403)
        self.assertContains(response, '<a class="button" href="/">Về trang chính</a>', status_code=403, html=True)
        self.assertIn('_auth_user_id', secure.session)
        self.assertEqual(secure.get('/accounts/login/').url, '/dashboard/')
        self.assertEqual(secure.get('/accounts/logout/').status_code, 405)
        self.assertEqual(secure.post('/accounts/logout/').status_code, 403)
        self.assertIn('_auth_user_id', secure.session)
        response = secure.post('/accounts/logout/', {
            'csrfmiddlewaretoken': secure.cookies['csrftoken'].value,
            'next': '/accounts/login/',
        }, follow=True)
        self.assertEqual(response.redirect_chain, [('/accounts/login/', 302)])
        self.assertContains(response, 'Chào mừng trở lại')
        self.assertNotIn('_auth_user_id', secure.session)
        self.assertEqual(secure.get('/dashboard/').status_code, 302)

    def test_public_header_offers_logout_only_to_signed_in_accounts(self):
        self.assertNotContains(self.client.get('/'), 'action="/accounts/logout/"')
        self.client.force_login(get_user_model().objects.create_user('unassigned'))
        self.assertContains(self.client.get('/'), 'action="/accounts/logout/"')

    def test_locked_database_has_retryable_error_page(self):
        from unittest.mock import patch
        from django.db import OperationalError
        self.client.force_login(self.coord)
        with patch('bridge.views.services.create_proposal', side_effect=OperationalError('database is locked')):
            self.assertContains(self.client.post('/coordination/'), 'Hệ thống đang bận', status_code=503)

    @override_settings(DEBUG=False)
    def test_error_pages(self):
        self.assertContains(self.client.get('/not-found/'), 'Không tìm thấy trang', status_code=404)
        self.client.force_login(self.teachers[1])
        self.assertContains(self.client.get('/coordination/'), 'Bạn chưa có quyền', status_code=403)

    @override_settings(DEBUG=False)
    def test_unexpected_error_renders_localized_500(self):
        from unittest.mock import patch
        self.client.force_login(self.coord)
        self.client.raise_request_exception = False
        with patch('bridge.views.scoped', side_effect=RuntimeError('Internal diagnostic, not for users')):
            response = self.client.get('/dashboard/')
        self.assertContains(response, 'Chưa thể xử lý yêu cầu', status_code=500)
        self.assertNotContains(response, 'Internal diagnostic', status_code=500)

    def test_audit_and_stock_cannot_be_changed_in_admin(self):
        admin = get_user_model().objects.create_superuser('admin', password='Test@2026')
        self.client.force_login(admin)
        event = Audit.objects.first()
        self.assertEqual(self.client.post(f'/admin/bridge/audit/{event.pk}/change/', {'notes': 'tamper'}).status_code, 403)
        self.assertEqual(self.client.post(f'/admin/bridge/inventory/{self.inv.pk}/change/', {'owned': 999}).status_code, 403)
        self.client.post(f'/admin/bridge/book/{self.book.pk}/change/', {'year': 2024})
        self.book.refresh_from_db()
        self.assertEqual(self.book.year, 2025)


class DemoTests(TestCase):
    def test_seed_is_idempotent_and_has_required_scenarios(self):
        from io import StringIO
        call_command('seed_demo', stdout=StringIO())
        count = Audit.objects.count()
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(Audit.objects.count(), count)
        self.assertEqual(School.objects.count(), 5)
        self.assertTrue(Loan.objects.filter(status='pending').exists())
        self.assertTrue(Loan.objects.filter(status='borrowed', return_by__lt=timezone.localdate()).exists())
        self.assertTrue(Loan.objects.filter(status='completed').exists())
        coord = get_user_model().objects.get(username='dieuphoi')
        self.client.force_login(coord)
        for path in ['/dashboard/', '/inventory/', '/requests/', '/coordination/', '/loans/']:
            self.assertEqual(self.client.get(path).status_code, 200)
