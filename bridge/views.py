from urllib.parse import urlencode
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import Q, F
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from . import services
from .access import accessible_loans, coordinator, require_coordinator, require_school, school_id
from .forms import InventoryForm, NeedForm
from .models import Audit, Book, Inventory, Loan, Need, Proposal, School


class VietnameseAuthenticationForm(AuthenticationForm):
    error_messages = {'invalid_login': 'Tên đăng nhập hoặc mật khẩu không đúng.', 'inactive': 'Tài khoản chưa được kích hoạt.'}

class BookBridgeLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = VietnameseAuthenticationForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        failures = getattr(self.request, 'axes_failures_since_start', None)
        if failures:
            context.update(login_failures=failures, login_limit=settings.AXES_FAILURE_LIMIT,
                           login_remaining=max(0, settings.AXES_FAILURE_LIMIT - failures))
        return context

def app_access(user):
    if not coordinator(user) and school_id(user) is None:
        raise PermissionDenied

def scoped(user, qs, field='school_id'):
    return qs if coordinator(user) else qs.filter(**{field: school_id(user)})

def paginated(request, qs):
    page = Paginator(qs, 20).get_page(request.GET.get('page'))
    query = request.GET.copy()
    query.pop('page', None)
    return {'page': page, 'page_query': query.urlencode()}

def filter_books(request, qs, prefix='book__'):
    q = request.GET.get('q', '').strip()[:200]
    if q:
        qs = qs.filter(Q(**{prefix + 'title__icontains': q}) | Q(**{prefix + 'subject__icontains': q}))
    grade = request.GET.get('grade', '')
    if grade.isdigit() and 1 <= int(grade) <= 12:
        qs = qs.filter(**{prefix + 'grade': int(grade)})
    for key in ['series', 'kind']:
        if request.GET.get(key):
            qs = qs.filter(**{prefix + key: request.GET[key][:150]})
    return qs

def filter_options():
    return {'grades': range(1, 13), 'series_options': Book.objects.values_list('series', flat=True).distinct().order_by('series'), 'kind_options': Book.Kind.choices}

def show_error(request, error):
    messages.error(request, ' '.join(error.messages) if isinstance(error, ValidationError) else 'Dữ liệu trùng hoặc đã thay đổi. Vui lòng tải lại và kiểm tra.')

def home(request):
    return render(request, 'home.html')

@login_required
def dashboard(request):
    app_access(request.user)
    inventories = scoped(request.user, Inventory.objects.select_related('book', 'school'))
    needs = scoped(request.user, Need.objects.filter(status=Need.Status.OPEN))
    loans = accessible_loans(request.user, Loan.objects.select_related('inventory__school', 'inventory__book', 'need__school'))
    active = loans.filter(status__in=['sent', 'borrowed', 'returning'])
    incoming = active if coordinator(request.user) else active.filter(need__school_id=school_id(request.user))
    outgoing = active if coordinator(request.user) else active.filter(inventory__school_id=school_id(request.user))
    # Incoming counts only books acknowledged as received; outgoing includes books in transit.
    metrics = [
        {'label': 'Có thể cho mượn', 'value': sum(i.available for i in inventories), 'url': '/inventory/?available=1', 'description': 'Sách sẵn sàng chia sẻ'},
        {'label': 'Nhu cầu còn thiếu', 'value': sum(n.remaining for n in needs), 'url': '/requests/?remaining=1', 'description': 'Chưa có nguồn giữ chỗ'},
        {'label': 'Đang cho mượn', 'value': sum(l.quantity for l in outgoing), 'url': '/loans/?direction=out&active=1', 'description': 'Bao gồm sách đang giao'},
        {'label': 'Đang mượn', 'value': sum(l.quantity for l in incoming.exclude(status='sent')), 'url': '/loans/?direction=in&borrowed=1', 'description': 'Đã nhận, chưa hoàn trả'},
    ]
    tasks = []
    for loan in loans.exclude(status__in=['completed', 'cancelled']):
        actions = [a for a in services.available_actions(request.user, loan) if a[0] not in ['issue', 'cancel', 'reject']]
        if actions or loan.overdue or loan.issue_open:
            tasks.append(loan)
        if len(tasks) == 6:
            break
    return render(request, 'dashboard.html', {'area': 'dashboard', 'metrics': metrics, 'tasks': tasks,
        'recent_loans': loans[:5], 'overdue_count': active.filter(return_by__lt=timezone.localdate()).count()})

@login_required
def inventory_list(request):
    app_access(request.user)
    qs = filter_books(request, scoped(request.user, Inventory.objects.select_related('book', 'school')))
    if request.GET.get('available'):
        qs = qs.filter(owned__gt=F('internal') + F('reserved') + F('lent'))
    return render(request, 'inventory_list.html', {'area': 'inventory', **filter_options(), **paginated(request, qs)})

@login_required
def inventory_form(request, pk=None):
    app_access(request.user)
    inv = get_object_or_404(Inventory, pk=pk) if pk else None
    if inv:
        require_school(request.user, inv.school_id)
    form = InventoryForm(request.POST or None, user=request.user, instance=inv)
    if request.method == 'POST' and form.is_valid():
        try:
            services.save_inventory(request.user, **form.cleaned_data, pk=pk)
        except (ValidationError, IntegrityError) as error:
            form.add_error(None, ' '.join(error.messages) if isinstance(error, ValidationError) else 'Kho của đầu sách này đã tồn tại. Hãy sửa bản ghi hiện có.')
        else:
            messages.success(request, 'Đã lưu kho sách và ghi nhật ký.')
            return redirect('inventory_list')
    history = Audit.objects.filter(inventory=inv).select_related('actor').order_by('-created_at')[:10] if inv else []
    return render(request, 'edit_form.html', {'area': 'inventory', 'form': form, 'title': 'Điều chỉnh kho sách' if inv else 'Khai báo kho sách',
        'back_url': '/inventory/', 'back_label': 'Kho sách', 'inventory': inv, 'history': history, 'inventory_form': True,
        'unavailable': inv.reserved + inv.lent if inv else 0})

@login_required
def need_list(request):
    app_access(request.user)
    qs = filter_books(request, scoped(request.user, Need.objects.select_related('book', 'school')))
    if request.GET.get('remaining'):
        qs = qs.filter(status='open', quantity__gt=F('received') + F('committed'))
    if request.GET.get('status') in Need.Status.values:
        qs = qs.filter(status=request.GET['status'])
    return render(request, 'need_list.html', {'area': 'requests', **filter_options(), 'need_statuses': Need.Status.choices, **paginated(request, qs)})

@login_required
def need_form(request, pk=None):
    app_access(request.user)
    need = get_object_or_404(Need, pk=pk) if pk else None
    if need:
        require_school(request.user, need.school_id)
        if need.status != Need.Status.OPEN:
            raise PermissionDenied
    form = NeedForm(request.POST or None, user=request.user, instance=need,
        initial=None if need else {'needed_by': timezone.localdate(), 'return_by': timezone.localdate() + timezone.timedelta(days=30)})
    if request.method == 'POST' and form.is_valid():
        try:
            services.save_need(request.user, **form.cleaned_data, pk=pk)
        except (ValidationError, IntegrityError) as error:
            form.add_error(None, ' '.join(error.messages) if isinstance(error, ValidationError) else 'Đã có nhu cầu đang mở cho đầu sách này.')
        else:
            messages.success(request, 'Đã lưu nhu cầu sách.')
            return redirect('need_list')
    return render(request, 'edit_form.html', {'area': 'requests', 'form': form,
        'title': 'Điều chỉnh nhu cầu' if need else 'Khai báo nhu cầu', 'back_url': '/requests/', 'back_label': 'Nhu cầu'})

@login_required
@require_POST
def need_cancel(request, pk):
    get_object_or_404(Need, pk=pk)
    try:
        services.cancel_need(request.user, pk)
    except ValidationError as error:
        show_error(request, error)
    else:
        messages.success(request, 'Đã hủy nhu cầu.')
    return redirect('need_list')

def scope_from(request):
    scope = {}
    book = request.GET.get('book', '')
    if book.isdigit() and Book.objects.filter(pk=int(book)).exists():
        scope['book'] = int(book)
    for key in ['province', 'locality']:
        if request.GET.get(key):
            scope[key] = request.GET[key][:100]
    return scope

@login_required
def coordination(request):
    require_coordinator(request.user)
    scope = scope_from(request)
    if request.method == 'POST':
        try:
            proposal = services.create_proposal(request.user, scope)
        except ValidationError as error:
            show_error(request, error)
        else:
            return redirect('proposal_detail', pk=proposal.pk)
    needs, inventories, _ = services.matching_data(scope)
    return render(request, 'coordination.html', {'area': 'coordination', 'scope': scope,
        'books': Book.objects.all(), 'provinces': School.objects.values_list('province', flat=True).distinct().order_by('province'),
        'localities': School.objects.values_list('locality', flat=True).distinct().order_by('locality'),
        'sources': [i for i in inventories if i.available > 0], 'needs': [n for n in needs if n.remaining > 0],
        'proposals': Proposal.objects.order_by('-pk')[:10]})

@login_required
def proposal_detail(request, pk):
    require_coordinator(request.user)
    proposal = get_object_or_404(Proposal, pk=pk)
    posted_quantities = {}
    if request.method == 'POST':
        try:
            if request.POST.get('action') == 'approve':
                services.approve_proposal(request.user, pk)
                messages.success(request, 'Đã duyệt và giữ chỗ. Hai điểm trường có thể xác nhận phiếu mượn.')
                return redirect('proposal_detail', pk=pk)
            if request.POST.get('action') != 'edit':
                raise ValidationError('Thao tác không hợp lệ.')
            for line in proposal.lines.all():
                value = request.POST.get(f'quantity_{line.pk}', '')
                if not value.isdigit() or int(value) <= 0:
                    raise ValidationError('Số lượng phải là số nguyên lớn hơn 0.')
                posted_quantities[line.pk] = int(value)
            services.edit_proposal(request.user, pk, posted_quantities, request.POST.get('reason', '')[:2000])
            messages.success(request, 'Đã lưu điều chỉnh; đề xuất chưa giữ sách.')
            return redirect('proposal_detail', pk=pk)
        except (ValidationError, IntegrityError) as error:
            show_error(request, error)
    proposal.refresh_from_db()
    lines = list(proposal.lines.select_related('inventory__school', 'inventory__book', 'need__school'))
    for line in lines:
        line.input_quantity = request.POST.get(f'quantity_{line.pk}', line.quantity)
    return render(request, 'proposal_detail.html', {'area': 'coordination', 'proposal': proposal, 'lines': lines,
        'total': sum(l.quantity for l in lines), 'reason': request.POST.get('reason', proposal.reason),
        'recompute_url': '/coordination/?' + urlencode(proposal.snapshot['scope'])})

@login_required
def loan_list(request):
    app_access(request.user)
    qs = accessible_loans(request.user, Loan.objects.select_related('inventory__school', 'inventory__book', 'need__school'))
    if request.GET.get('status') in Loan.Status.values:
        qs = qs.filter(status=request.GET['status'])
    sid = school_id(request.user)
    if not coordinator(request.user):
        if request.GET.get('direction') == 'in':
            qs = qs.filter(need__school_id=sid)
        elif request.GET.get('direction') == 'out':
            qs = qs.filter(inventory__school_id=sid)
    if request.GET.get('active'):
        qs = qs.filter(status__in=['sent', 'borrowed', 'returning'])
    if request.GET.get('borrowed'):
        qs = qs.filter(status__in=['borrowed', 'returning'])
    if request.GET.get('overdue'):
        qs = qs.filter(status__in=['sent', 'borrowed', 'returning'], return_by__lt=timezone.localdate())
    q = request.GET.get('q', '').strip()[:200]
    if q:
        if q.upper().startswith('BB-') and q[3:].isdigit():
            qs = qs.filter(pk=int(q[3:]))
        else:
            qs = qs.filter(Q(inventory__book__title__icontains=q) | Q(need__school__name__icontains=q) | Q(inventory__school__name__icontains=q))
    return render(request, 'loan_list.html', {'area': 'loans', 'loan_statuses': Loan.Status.choices, **paginated(request, qs)})

@login_required
def loan_detail(request, pk):
    app_access(request.user)
    loan = get_object_or_404(Loan.objects.select_related('inventory__school', 'inventory__book', 'need__school'), pk=pk)
    if not coordinator(request.user) and (school_id(request.user) is None or school_id(request.user) not in [loan.inventory.school_id, loan.need.school_id]):
        raise PermissionDenied
    if request.method == 'POST':
        try:
            services.transition(request.user, pk, request.POST.get('action'), request.POST.get('notes', '')[:2000])
        except ValidationError as error:
            show_error(request, error)
        else:
            messages.success(request, 'Đã cập nhật phiếu và ghi nhận người xác nhận.')
            return redirect('loan_detail', pk=pk)
        loan.refresh_from_db()
    return render(request, 'loan_detail.html', {'area': 'loans', 'loan': loan,
        'actions': services.available_actions(request.user, loan), 'events': loan.events.select_related('actor'),
        'notes': request.POST.get('notes', '')})

def error403(request, exception=None):
    return render(request, 'error.html', {'code': '403', 'title': 'Bạn chưa có quyền truy cập', 'description': 'Trang này nằm ngoài phạm vi tài khoản. Liên hệ quản trị viên nếu cần điều chỉnh phân quyền.'}, status=403)

def error404(request, exception=None):
    return render(request, 'error.html', {'code': '404', 'title': 'Không tìm thấy trang', 'description': 'Đường dẫn không tồn tại hoặc dữ liệu đã được thay đổi.'}, status=404)

def error500(request):
    return render(request, 'error.html', {'code': '500', 'title': 'Chưa thể xử lý yêu cầu', 'description': 'Vui lòng thử lại hoặc liên hệ quản trị viên. Kiểm tra lại dữ liệu trước khi tiếp tục.'}, status=500)

def csrf_failure(request, reason=''):
    return render(request, 'error.html', {'code': '403', 'title': 'Phiên xác nhận đã hết hạn',
        'description': 'Dữ liệu chưa được gửi. Quay lại, tải lại trang rồi thử lại để nhận phiên xác nhận mới.'}, status=403)
