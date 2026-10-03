from django.conf import settings
from django.db import models
from django.db.models import Q, F
from django.utils import timezone


class School(models.Model):
    code = models.CharField('Mã điểm trường', max_length=30, unique=True)
    name = models.CharField('Tên điểm trường', max_length=200)
    province = models.CharField('Tỉnh / thành phố', max_length=100)
    locality = models.CharField('Địa bàn', max_length=100)
    contact_name = models.CharField('Người liên hệ', max_length=100)
    contact_phone = models.CharField('Số điện thoại', max_length=30, blank=True)
    contact_email = models.EmailField('Email', blank=True)

    class Meta:
        ordering = ['code']
        verbose_name = 'Điểm trường'
        verbose_name_plural = 'Điểm trường'

    def __str__(self):
        return self.name


class Profile(models.Model):
    class Role(models.TextChoices):
        TEACHER = 'teacher', 'Giáo viên'
        COORDINATOR = 'coordinator', 'Điều phối viên'

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField('Vai trò', max_length=20, choices=Role.choices, default=Role.TEACHER)
    school = models.ForeignKey(School, verbose_name='Điểm trường', on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        verbose_name = 'Phân quyền tài khoản'
        verbose_name_plural = 'Phân quyền tài khoản'
        constraints = [models.CheckConstraint(condition=Q(role='coordinator') | Q(school__isnull=False), name='teacher_requires_school')]

    def __str__(self):
        return f'{self.user} · {self.get_role_display()}'


class Book(models.Model):
    class Kind(models.TextChoices):
        TEXTBOOK = 'textbook', 'Sách giáo khoa'
        WORKBOOK = 'workbook', 'Sách bài tập'

    title = models.CharField('Tên sách', max_length=200)
    subject = models.CharField('Môn học', max_length=100)
    grade = models.PositiveSmallIntegerField('Lớp')
    series = models.CharField('Bộ sách', max_length=150)
    publisher = models.CharField('Nhà xuất bản', max_length=150)
    year = models.PositiveSmallIntegerField('Năm xuất bản')
    kind = models.CharField('Loại sách', max_length=20, choices=Kind.choices, default=Kind.TEXTBOOK)

    class Meta:
        ordering = ['grade', 'title', 'year']
        verbose_name = 'Đầu sách'
        verbose_name_plural = 'Đầu sách'
        constraints = [
            models.UniqueConstraint(fields=['title', 'subject', 'grade', 'series', 'publisher', 'year', 'kind'], name='unique_book_edition'),
            models.CheckConstraint(condition=Q(grade__gte=1, grade__lte=12), name='grade_range'),
            models.CheckConstraint(condition=Q(year__gte=1900, year__lte=2100), name='year_range'),
        ]

    def __str__(self):
        return f'{self.title} · Lớp {self.grade} · {self.series} · {self.year}'


class Inventory(models.Model):
    school = models.ForeignKey(School, on_delete=models.PROTECT, verbose_name='Điểm trường')
    book = models.ForeignKey(Book, on_delete=models.PROTECT, verbose_name='Đầu sách')
    owned = models.PositiveIntegerField('Số sở hữu', default=0)
    internal = models.PositiveIntegerField('Dùng nội bộ', default=0)
    reserved = models.PositiveIntegerField('Giữ chỗ', default=0)
    lent = models.PositiveIntegerField('Đang cho mượn / đang giao', default=0)
    version = models.PositiveIntegerField(default=0)

    @property
    def available(self):
        return self.owned - self.internal - self.reserved - self.lent

    class Meta:
        ordering = ['book__grade', 'book__title', 'school__code']
        verbose_name = 'Kho sách'
        verbose_name_plural = 'Kho sách'
        constraints = [
            models.UniqueConstraint(fields=['school', 'book'], name='unique_school_inventory'),
            models.CheckConstraint(condition=Q(owned__gte=F('internal') + F('reserved') + F('lent')), name='inventory_nonnegative_available'),
        ]

    def __str__(self):
        return f'{self.school} · {self.book}'


class Need(models.Model):
    class Status(models.TextChoices):
        OPEN = 'open', 'Đang cần sách'
        FULFILLED = 'fulfilled', 'Đã đáp ứng'
        CANCELLED = 'cancelled', 'Đã hủy'

    school = models.ForeignKey(School, on_delete=models.PROTECT, verbose_name='Điểm trường')
    book = models.ForeignKey(Book, on_delete=models.PROTECT, verbose_name='Đầu sách')
    quantity = models.PositiveIntegerField('Số cuốn cần bổ sung')
    received = models.PositiveIntegerField(default=0)
    committed = models.PositiveIntegerField(default=0)
    needed_by = models.DateField('Ngày cần sách')
    return_by = models.DateField('Ngày dự kiến trả')
    notes = models.TextField('Ghi chú', blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(default=timezone.now)
    version = models.PositiveIntegerField(default=0)

    @property
    def remaining(self):
        return self.quantity - self.received - self.committed

    @property
    def ratio(self):
        return round(100 * (self.received + self.committed) / self.quantity)

    class Meta:
        ordering = ['created_at', 'pk']
        verbose_name = 'Nhu cầu'
        verbose_name_plural = 'Nhu cầu'
        constraints = [
            models.UniqueConstraint(fields=['school', 'book'], condition=Q(status='open'), name='one_open_need'),
            models.CheckConstraint(condition=Q(quantity__gt=0), name='need_positive'),
            models.CheckConstraint(condition=Q(quantity__gte=F('received') + F('committed')), name='need_not_overfilled'),
            models.CheckConstraint(condition=Q(return_by__gte=F('needed_by')), name='need_date_order'),
        ]

    def __str__(self):
        return f'{self.school} · {self.book} · {self.quantity} cuốn'


class Proposal(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Chưa duyệt'
        APPROVED = 'approved', 'Đã duyệt'

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    snapshot = models.JSONField(default=dict)
    reason = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Đề xuất phân bổ'
        verbose_name_plural = 'Đề xuất phân bổ'

    def __str__(self):
        return f'Đề xuất #{self.pk}'


class ProposalLine(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='lines')
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT)
    need = models.ForeignKey(Need, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    before_percent = models.PositiveSmallIntegerField()
    after_percent = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['pk']
        verbose_name = 'Dòng phân bổ'
        verbose_name_plural = 'Dòng phân bổ'
        constraints = [
            models.UniqueConstraint(fields=['proposal', 'inventory', 'need'], name='unique_proposal_pair'),
            models.CheckConstraint(condition=Q(quantity__gt=0), name='proposal_quantity_positive'),
        ]


class Loan(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Chờ xác nhận'
        READY = 'ready', 'Sẵn sàng giao'
        SENT = 'sent', 'Đã gửi'
        BORROWED = 'borrowed', 'Đang mượn'
        RETURNING = 'returning', 'Đang hoàn trả'
        COMPLETED = 'completed', 'Hoàn tất'
        CANCELLED = 'cancelled', 'Đã hủy'

    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT)
    need = models.ForeignKey(Need, on_delete=models.PROTECT)
    proposal_line = models.OneToOneField(ProposalLine, on_delete=models.PROTECT, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    lender_confirmed = models.BooleanField(default=False)
    borrower_confirmed = models.BooleanField(default=False)
    return_by = models.DateField()
    created_at = models.DateTimeField(default=timezone.now)
    issue_open = models.BooleanField(default=False)

    @property
    def code(self):
        return f'BB-{self.pk:05d}'

    @property
    def overdue(self):
        return self.status in ['sent', 'borrowed', 'returning'] and self.return_by < timezone.localdate()

    class Meta:
        ordering = ['-created_at', '-pk']
        verbose_name = 'Phiếu mượn'
        verbose_name_plural = 'Phiếu mượn'
        constraints = [models.CheckConstraint(condition=Q(quantity__gt=0), name='loan_positive')]

    def __str__(self):
        return self.code


class Audit(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    loan = models.ForeignKey(Loan, on_delete=models.PROTECT, null=True, blank=True, related_name='events')
    inventory = models.ForeignKey(Inventory, on_delete=models.PROTECT, null=True, blank=True)
    need = models.ForeignKey(Need, on_delete=models.PROTECT, null=True, blank=True)
    action = models.CharField('Hành động', max_length=150)
    notes = models.TextField('Ghi chú', blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['created_at', 'pk']
        verbose_name = 'Nhật ký nghiệp vụ'
        verbose_name_plural = 'Nhật ký nghiệp vụ'
