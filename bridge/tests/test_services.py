from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, IntegrityError, transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from bridge import services
from bridge.models import Audit, Book, Inventory, Loan, Need, Profile, ProposalLine, School


class FixtureMixin:
    def fixture(self):
        self.today = timezone.localdate()
        self.schools = [School.objects.create(code=f'S{i}', name=f'Trường {i}', province='A', locality='X', contact_name='Giáo viên') for i in range(4)]
        self.coord = get_user_model().objects.create_user('coord', password='Test@2026')
        Profile.objects.create(user=self.coord, role='coordinator')
        self.teachers = []
        for i, school in enumerate(self.schools):
            user = get_user_model().objects.create_user(f'teacher{i}', password='Test@2026')
            Profile.objects.create(user=user, school=school)
            self.teachers.append(user)
        self.book = Book.objects.create(title='Toán', subject='Toán', grade=3, series='A', publisher='NXB', year=2025)
        self.inv = services.save_inventory(self.coord, self.schools[0], self.book, 50, 30, 'Khởi tạo')
        self.n1 = services.save_need(self.coord, self.schools[1], self.book, 10, self.today, self.today + timedelta(days=30), '')
        self.n2 = services.save_need(self.coord, self.schools[2], self.book, 30, self.today, self.today + timedelta(days=30), '')

    def approved(self):
        proposal = services.create_proposal(self.coord)
        return services.approve_proposal(self.coord, proposal.pk)


class ServiceTests(FixtureMixin, TestCase):
    def setUp(self):
        self.fixture()

    def test_fairness_and_draft_does_not_reserve(self):
        p = services.create_proposal(self.coord)
        self.assertEqual(dict(p.lines.values_list('need_id', 'quantity')), {self.n1.pk: 5, self.n2.pk: 15})
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.reserved, 0)
        self.assertEqual(set(p.lines.values_list('after_percent', flat=True)), {50})

    def test_complete_round_trip_and_repeat_posts(self):
        loans = self.approved()
        loan = next(l for l in loans if l.need_id == self.n1.pk)
        teacher = self.teachers[1]
        self.inv.refresh_from_db()
        self.assertEqual((self.inv.reserved, self.inv.available), (20, 0))
        services.transition(self.teachers[0], loan.pk, 'confirm_lender')
        with self.assertRaises(ValidationError):
            services.transition(self.teachers[0], loan.pk, 'confirm_lender')
        with self.assertRaises(ValidationError):
            services.transition(self.teachers[0], loan.pk, 'send')
        services.transition(teacher, loan.pk, 'confirm_borrower')
        services.transition(self.teachers[0], loan.pk, 'send')
        self.inv.refresh_from_db()
        self.assertEqual((self.inv.reserved, self.inv.lent), (15, 5))
        services.transition(teacher, loan.pk, 'receive')
        self.n1.refresh_from_db()
        self.assertEqual((self.n1.received, self.n1.committed), (5, 0))
        with self.assertRaises(ValidationError):
            services.transition(teacher, loan.pk, 'receive')
        services.transition(teacher, loan.pk, 'return')
        services.transition(self.teachers[0], loan.pk, 'complete')
        with self.assertRaises(ValidationError):
            services.transition(self.teachers[0], loan.pk, 'complete')
        self.inv.refresh_from_db()
        self.assertEqual((self.inv.owned, self.inv.internal, self.inv.reserved, self.inv.lent, self.inv.available), (50, 30, 15, 0, 5))
        second = next(l for l in loans if l.need_id == self.n2.pk)
        services.transition(self.coord, second.pk, 'cancel', 'Không cần nữa')
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.available, 20)
        self.assertEqual(Audit.objects.filter(loan=loan, action='Xác nhận đã nhận đủ').count(), 1)
        self.assertFalse(Inventory.objects.filter(school=self.schools[1]).exists())

    def test_stale_proposal_and_duplicate_approval(self):
        p1, p2 = services.create_proposal(self.coord), services.create_proposal(self.coord)
        services.approve_proposal(self.coord, p1.pk)
        with self.assertRaises(ValidationError):
            services.approve_proposal(self.coord, p2.pk)
        with self.assertRaises(ValidationError):
            services.approve_proposal(self.coord, p1.pk)
        self.assertEqual(Loan.objects.count(), 2)
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.reserved, 20)

    def test_inventory_or_need_change_invalidates_snapshot(self):
        p = services.create_proposal(self.coord)
        services.save_inventory(self.coord, self.schools[0], self.book, 51, 30, 'Thêm sách', self.inv.pk, self.inv.version)
        with self.assertRaisesMessage(ValidationError, 'lỗi thời'):
            services.approve_proposal(self.coord, p.pk)
        self.assertEqual(Loan.objects.count(), 0)

    def test_added_source_invalidates_snapshot(self):
        p = services.create_proposal(self.coord)
        services.save_inventory(self.coord, self.schools[3], self.book, 5, 0, '')
        with self.assertRaisesMessage(ValidationError, 'lỗi thời'):
            services.approve_proposal(self.coord, p.pk)

    def test_edit_requires_reason_and_checks_capacity(self):
        p = services.create_proposal(self.coord)
        line = p.lines.first()
        with self.assertRaises(ValidationError):
            services.edit_proposal(self.coord, p.pk, {line.pk: 100}, 'Điều chỉnh')
        with self.assertRaises(ValidationError):
            services.edit_proposal(self.coord, p.pk, {line.pk: 1}, '')
        services.edit_proposal(self.coord, p.pk, {line.pk: 1}, 'Ưu tiên giai đoạn đầu')
        services.approve_proposal(self.coord, p.pk)
        self.assertEqual(Loan.objects.get(proposal_line=line).quantity, 1)

    def test_source_and_need_limits_are_checked_independently(self):
        p = services.create_proposal(self.coord)
        line = p.lines.get(need=self.n2)
        with self.assertRaisesMessage(ValidationError, 'vượt số sách'):
            services.edit_proposal(self.coord, p.pk, {line.pk: 20}, 'Vượt nguồn nhưng chưa vượt nhu cầu')
        services.cancel_need(self.coord, self.n2.pk)
        p = services.create_proposal(self.coord)
        line = p.lines.get(need=self.n1)
        with self.assertRaisesMessage(ValidationError, 'vượt nhu cầu'):
            services.edit_proposal(self.coord, p.pk, {line.pk: 11}, 'Nguồn đủ nhưng nhu cầu chỉ 10')

    def test_committed_need_cannot_be_cancelled_or_reduced(self):
        self.approved()
        self.n1.refresh_from_db()
        with self.assertRaises(ValidationError):
            services.cancel_need(self.teachers[1], self.n1.pk)
        with self.assertRaisesMessage(ValidationError, 'không nhỏ hơn'):
            services.save_need(self.teachers[1], self.n1.school, self.book, 1, self.today,
                self.today + timedelta(days=30), '', self.n1.pk, self.n1.version)

    def test_reject_releases_need_and_source_and_requires_reason(self):
        loan = self.approved()[0]
        user = self.teachers[self.schools.index(loan.need.school)]
        with self.assertRaises(ValidationError):
            services.transition(user, loan.pk, 'reject')
        services.transition(user, loan.pk, 'reject', 'Đã có sách mới')
        self.assertEqual(Inventory.objects.get(pk=self.inv.pk).available, loan.quantity)
        self.assertEqual(Need.objects.get(pk=loan.need_id).committed, 0)

    def test_permission_boundary_in_services(self):
        with self.assertRaises(PermissionDenied):
            services.create_proposal(self.teachers[1])
        with self.assertRaises(PermissionDenied):
            services.save_inventory(self.teachers[1], self.schools[0], self.book, 100, 0, 'Xâm nhập', self.inv.pk, self.inv.version)
        loan = self.approved()[0]
        with self.assertRaises(PermissionDenied):
            services.transition(self.teachers[3], loan.pk, 'cancel', 'Xâm nhập')
        with self.assertRaises(ValidationError):
            services.transition(self.coord, loan.pk, 'confirm_lender')

    def test_issue_pauses_delivery_and_resolution_is_audited(self):
        loan = self.approved()[0]
        services.transition(self.teachers[0], loan.pk, 'issue', 'Cần kiểm tra tình trạng sách')
        with self.assertRaises(ValidationError):
            services.transition(self.teachers[0], loan.pk, 'confirm_lender')
        with self.assertRaises(ValidationError):
            services.transition(self.teachers[0], loan.pk, 'resolve', 'Đã kiểm tra')
        services.transition(self.coord, loan.pk, 'resolve', 'Hai trường đã kiểm tra đủ số lượng')
        services.transition(self.teachers[0], loan.pk, 'confirm_lender')
        self.assertFalse(Loan.objects.get(pk=loan.pk).issue_open)

    def test_exact_edition_no_self_match_and_no_source(self):
        other = Book.objects.create(title='Toán', subject='Toán', grade=3, series='A', publisher='NXB', year=2024)
        services.save_inventory(self.coord, self.schools[1], other, 100, 0, '')
        pairs, totals = services.allocate([self.n1], [Inventory(school=self.schools[1], book=self.book, pk=900, owned=10)])
        self.assertFalse(pairs)
        self.assertFalse(services.allocate([self.n1], [Inventory(school=self.schools[0], book=other, pk=901, owned=100)])[0])
        self.assertFalse(services.allocate([self.n1], [])[0])

    def test_locality_preference(self):
        self.schools[0].locality = 'Far'
        self.schools[0].save()
        near = services.save_inventory(self.coord, self.schools[3], self.book, 40, 0, '')
        p = services.create_proposal(self.coord)
        self.assertEqual(set(p.lines.values_list('inventory_id', flat=True)), {near.pk})

    def test_inventory_edit_cannot_reduce_below_commitments_or_repeat_stale_edit(self):
        self.approved()
        inv = Inventory.objects.get(pk=self.inv.pk)
        with self.assertRaises(ValidationError):
            services.save_inventory(self.coord, inv.school, inv.book, 40, 30, 'Giảm', inv.pk, inv.version)
        with self.assertRaises(ValidationError):
            services.save_inventory(self.coord, inv.school, inv.book, 60, 30, 'Sửa cũ', inv.pk, 0)

    def test_date_validation_cancel_and_open_need_uniqueness(self):
        with self.assertRaises(ValidationError):
            services.save_need(self.coord, self.schools[1], self.book, 20, self.today, self.today + timedelta(days=10), '')
        with self.assertRaises(ValidationError):
            services.save_need(self.coord, self.schools[3], self.book, 1, self.today, self.today - timedelta(days=1), '')
        services.cancel_need(self.teachers[1], self.n1.pk)
        self.assertEqual(Need.objects.get(pk=self.n1.pk).status, 'cancelled')
        services.save_need(self.coord, self.schools[1], self.book, 2, self.today, self.today + timedelta(days=10), '')

    def test_completed_need_does_not_reopen_on_return(self):
        services.cancel_need(self.coord, self.n2.pk)
        loan = self.approved()[0]
        for user, action in [(self.teachers[0], 'confirm_lender'), (self.teachers[1], 'confirm_borrower'),
                (self.teachers[0], 'send'), (self.teachers[1], 'receive'), (self.teachers[1], 'return'), (self.teachers[0], 'complete')]:
            services.transition(user, loan.pk, action)
        self.n1.refresh_from_db()
        self.inv.refresh_from_db()
        self.assertEqual(self.n1.status, 'fulfilled')
        self.assertEqual(self.n1.received, 10)
        self.assertEqual(self.inv.available, 20)

    def test_cross_edition_proposal_tampering_is_rejected(self):
        p = services.create_proposal(self.coord, {'book': self.book.pk})
        line = p.lines.first()
        line.need_id = self.n2.pk if line.need_id == self.n1.pk else self.n1.pk
        # Same-book tampering is capacity-checked; different-book tampering always fails.
        other = Book.objects.create(title='Tiếng Việt', subject='TV', grade=3, series='A', publisher='NXB', year=2025)
        need = services.save_need(self.coord, self.schools[3], other, 10, self.today, self.today + timedelta(days=10), '')
        line.need_id = need.pk
        with self.assertRaisesMessage(ValidationError, 'Nguồn và nhu cầu không phù hợp'):
            services.validate_proposal(p, [line])


class ConcurrencyTests(FixtureMixin, TransactionTestCase):
    def setUp(self):
        self.fixture()

    def test_two_simultaneous_approvals_reserve_only_once(self):
        p1, p2 = services.create_proposal(self.coord), services.create_proposal(self.coord)
        barrier = Barrier(2)
        def worker(pk):
            close_old_connections()
            try:
                user = get_user_model().objects.get(pk=self.coord.pk)
                barrier.wait(timeout=10)
                try:
                    services.approve_proposal(user, pk)
                    return 'approved'
                except ValidationError:
                    return 'stale'
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(worker, [p1.pk, p2.pk]))
        self.assertCountEqual(results, ['approved', 'stale'])
        self.inv.refresh_from_db()
        self.assertEqual(self.inv.reserved, 20)
        self.assertEqual(Loan.objects.count(), 2)
