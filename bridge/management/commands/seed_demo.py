import os
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from bridge.models import Book, Need, Profile, School
from bridge import services


class Command(BaseCommand):
    help = 'Tạo dữ liệu và tài khoản demo trên database trống, không xóa dữ liệu hiện có.'

    @transaction.atomic
    def handle(self, *args, **options):
        if School.objects.filter(code='DEMO-01').exists():
            self.stdout.write('Dữ liệu demo đã tồn tại; không thay đổi dữ liệu.')
            return
        if School.objects.exists() or get_user_model().objects.exists():
            raise CommandError('Lệnh demo chỉ chạy trên database mới. Dùng database riêng để tránh trộn dữ liệu thật.')
        password = os.environ.get('BOOKBRIDGE_DEMO_PASSWORD', 'Demo@2026')
        users = get_user_model()
        admin = users.objects.create_superuser('admin', email='', password=password, first_name='Quản trị', last_name='BookBridge')
        coord = users.objects.create_user('dieuphoi', password=password, first_name='Minh', last_name='Điều phối')
        Profile.objects.create(user=coord, role='coordinator')
        names = ['Tiểu học Hòa Bình', 'Tiểu học Bình Minh', 'Tiểu học Suối Đá', 'Tiểu học Tân Phú', 'Tiểu học An Lạc']
        teachers, schools = [], []
        for idx, name in enumerate(names, 1):
            school = School.objects.create(code=f'DEMO-{idx:02d}', name=name,
                province='Địa phương mẫu A' if idx < 5 else 'Địa phương mẫu B',
                locality='Khu vực 1' if idx <= 3 else 'Khu vực 2', contact_name=f'Giáo viên demo {idx}')
            teacher = users.objects.create_user(f'giaovien{idx}', password=password, first_name=f'Giáo viên {idx}', last_name='Demo')
            Profile.objects.create(user=teacher, school=school)
            schools.append(school)
            teachers.append(teacher)
        today = timezone.localdate()
        specs = [
            ('Toán 3', 'Toán', 3, 'textbook'), ('Tiếng Việt 3 · Tập 1', 'Tiếng Việt', 3, 'textbook'),
            ('Tự nhiên và Xã hội 3', 'Tự nhiên và Xã hội', 3, 'textbook'), ('Bài tập Toán 3', 'Toán', 3, 'workbook'),
            ('Lịch sử và Địa lí 4', 'Lịch sử và Địa lí', 4, 'textbook'), ('Tiếng Anh 4', 'Tiếng Anh', 4, 'textbook'),
            ('Đạo đức 3', 'Đạo đức', 3, 'textbook'), ('Khoa học 4', 'Khoa học', 4, 'textbook'),
        ]
        books = [Book.objects.create(title=title, subject=subject, grade=grade, series='Bộ sách minh họa',
            publisher='Danh mục demo', year=2025, kind=kind) for title, subject, grade, kind in specs]
        # 20 available books shared across requests of 10 and 30 -> 5 and 15.
        services.save_inventory(admin, schools[0], books[0], 50, 30, 'Khởi tạo dữ liệu demo')
        for school, q in [(schools[1], 10), (schools[2], 30)]:
            services.save_need(admin, school, books[0], q, today + timedelta(days=2), today + timedelta(days=30), 'Nhu cầu minh họa')
        services.create_proposal(coord, {'book': books[0].pk})

        stages = ['pending', 'borrowed', 'sent', 'overdue', 'completed', 'ready', 'returning']
        for book, stage in zip(books[1:], stages):
            services.save_inventory(admin, schools[0], book, 35, 20, 'Khởi tạo dữ liệu demo')
            recipient_idx = 1 if stage in ['pending', 'completed', 'ready'] else 2
            if stage == 'returning':
                recipient_idx = 4
            school, teacher = schools[recipient_idx], teachers[recipient_idx]
            needed = today - timedelta(days=25) if stage == 'overdue' else today + timedelta(days=1)
            due = today - timedelta(days=2) if stage == 'overdue' else today + timedelta(days=30)
            need = Need.objects.create(school=school, book=book, quantity=8, needed_by=needed, return_by=due, notes='Dữ liệu demo, không phải thông tin trường thực tế.')
            services.audit(admin, 'Khởi tạo nhu cầu demo', need=need)
            proposal = services.create_proposal(coord, {'book': book.pk})
            loan = services.approve_proposal(coord, proposal.pk)[0]
            if stage == 'pending':
                continue
            services.transition(teachers[0], loan.pk, 'confirm_lender')
            services.transition(teacher, loan.pk, 'confirm_borrower')
            if stage == 'ready':
                continue
            services.transition(teachers[0], loan.pk, 'send')
            if stage == 'sent':
                continue
            services.transition(teacher, loan.pk, 'receive')
            if stage in ['completed', 'returning']:
                services.transition(teacher, loan.pk, 'return')
            if stage == 'completed':
                services.transition(teachers[0], loan.pk, 'complete')
        # A second edition and an additional source exercise exact-book matching.
        other = Book.objects.create(title='Toán 3', subject='Toán', grade=3, series='Bộ sách minh họa', publisher='Danh mục demo', year=2024)
        services.save_inventory(admin, schools[3], other, 30, 15, 'Khác năm xuất bản, không ghép với Toán 3 năm 2025')
        self.stdout.write(self.style.SUCCESS('Đã tạo 5 điểm trường, 9 đầu sách và đầy đủ trạng thái demo.'))
        self.stdout.write('Tài khoản: admin, dieuphoi, giaovien1 … giaovien5. Mật khẩu lấy từ BOOKBRIDGE_DEMO_PASSWORD, mặc định Demo@2026.')
