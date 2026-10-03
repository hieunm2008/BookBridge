from collections import defaultdict
from fractions import Fraction
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone
from .access import coordinator, require_coordinator, require_school, school_id
from .models import Audit, Inventory, Loan, Need, Proposal, ProposalLine


def audit(user, action, **kwargs):
    return Audit.objects.create(actor=user, action=action, **kwargs)


@transaction.atomic
def save_inventory(user, school, book, owned, internal, reason, pk=None, version=None):
    require_school(user, school.pk)
    inv = Inventory.objects.get(pk=pk) if pk else Inventory(school=school, book=book)
    if pk:
        require_school(user, inv.school_id)
        if inv.school_id != school.pk or inv.book_id != book.pk:
            raise ValidationError('Không thể đổi trường hoặc đầu sách của bản ghi kho.')
        if inv.version != version:
            raise ValidationError('Kho đã thay đổi. Vui lòng tải lại trước khi sửa.')
        if not reason.strip():
            raise ValidationError('Hãy ghi lý do điều chỉnh kho.')
    before = f'Sở hữu {inv.owned}, nội bộ {inv.internal}'
    if owned < 0 or internal < 0 or owned < internal + inv.reserved + inv.lent:
        raise ValidationError('Số sở hữu phải đủ cho sách dùng nội bộ, giữ chỗ và đang cho mượn.')
    inv.owned, inv.internal = owned, internal
    inv.version += 1
    inv.full_clean()
    inv.save()
    audit(user, 'Khai báo kho' if not pk else 'Điều chỉnh kho', inventory=inv,
          notes=f'{before} → Sở hữu {owned}, nội bộ {internal}. {reason}')
    return inv


@transaction.atomic
def save_need(user, school, book, quantity, needed_by, return_by, notes, pk=None, version=None):
    require_school(user, school.pk)
    need = Need.objects.get(pk=pk) if pk else Need(school=school, book=book)
    if pk:
        require_school(user, need.school_id)
        if need.status != Need.Status.OPEN:
            raise ValidationError('Chỉ sửa được nhu cầu đang mở.')
        if need.version != version:
            raise ValidationError('Nhu cầu đã thay đổi. Vui lòng tải lại trước khi sửa.')
        if (need.school_id, need.book_id) != (school.pk, book.pk):
            raise ValidationError('Không thể đổi trường hoặc đầu sách của nhu cầu.')
    if needed_by > return_by:
        raise ValidationError('Ngày trả phải bằng hoặc sau ngày cần sách.')
    if quantity <= 0 or quantity < need.received + need.committed:
        raise ValidationError('Số cuốn phải lớn hơn 0 và không nhỏ hơn tổng đã nhận, giữ chỗ hoặc đang giao.')
    if not pk and return_by < timezone.localdate():
        raise ValidationError('Ngày trả không được ở quá khứ.')
    need.quantity, need.needed_by, need.return_by, need.notes = quantity, needed_by, return_by, notes
    if quantity == need.received:
        need.status = Need.Status.FULFILLED
    need.version += 1
    need.full_clean()
    need.save()
    audit(user, 'Khai báo nhu cầu' if not pk else 'Điều chỉnh nhu cầu', need=need,
          notes=f'{quantity} cuốn; cần {needed_by}; trả {return_by}. {notes}')
    return need


@transaction.atomic
def cancel_need(user, pk):
    need = Need.objects.get(pk=pk)
    require_school(user, need.school_id)
    if need.status != Need.Status.OPEN or need.committed:
        raise ValidationError('Chỉ hủy nhu cầu đang mở và không có phiếu giữ chỗ/đang giao.')
    need.status = Need.Status.CANCELLED
    need.version += 1
    need.save()
    audit(user, 'Hủy nhu cầu', need=need)


def matching_data(scope):
    needs = Need.objects.filter(status=Need.Status.OPEN).select_related('school', 'book')
    if scope.get('book'):
        needs = needs.filter(book_id=scope['book'])
    if scope.get('province'):
        needs = needs.filter(school__province=scope['province'])
    if scope.get('locality'):
        needs = needs.filter(school__locality=scope['locality'])
    needs = list(needs.order_by('created_at', 'pk'))
    book_ids = {n.book_id for n in needs}
    inventories = list(Inventory.objects.filter(book_id__in=book_ids).select_related('school', 'book').order_by('pk'))
    snapshot = {
        'scope': scope,
        'needs': [[n.pk, n.version, n.quantity, n.received, n.committed, str(n.needed_by), str(n.return_by), n.school.province, n.school.locality] for n in needs],
        'inventories': [[i.pk, i.version, i.available, i.school.province, i.school.locality] for i in inventories],
    }
    return needs, inventories, snapshot


def allocate(needs, inventories):
    supply = {i.pk: i.available for i in inventories}
    granted = defaultdict(int)
    pairs = defaultdict(int)
    by_book = defaultdict(list)
    for need in needs:
        if need.remaining > 0:
            by_book[need.book_id].append(need)
    for book_id, candidates in by_book.items():
        sources = [i for i in inventories if i.book_id == book_id]
        while True:
            eligible = [n for n in candidates if granted[n.pk] < n.remaining and
                        any(supply[i.pk] > 0 and i.school_id != n.school_id for i in sources)]
            if not eligible:
                break
            need = min(eligible, key=lambda n: (Fraction(n.received + n.committed + granted[n.pk], n.quantity), n.created_at, n.pk))
            source = min((i for i in sources if supply[i.pk] > 0 and i.school_id != need.school_id), key=lambda i: (
                0 if (i.school.province, i.school.locality) == (need.school.province, need.school.locality)
                else 1 if i.school.province == need.school.province else 2,
                i.school.code, i.pk,
            ))
            supply[source.pk] -= 1
            granted[need.pk] += 1
            pairs[(source.pk, need.pk)] += 1
    return pairs, granted


@transaction.atomic
def create_proposal(user, scope=None):
    require_coordinator(user)
    needs, inventories, snapshot = matching_data(scope or {})
    pairs, granted = allocate(needs, inventories)
    if not pairs:
        raise ValidationError('Chưa có nguồn phù hợp với nhu cầu còn thiếu trong phạm vi đã chọn.')
    proposal = Proposal.objects.create(created_by=user, snapshot=snapshot)
    indexed = {n.pk: n for n in needs}
    for (inventory_id, need_id), quantity in pairs.items():
        need = indexed[need_id]
        ProposalLine.objects.create(proposal=proposal, inventory_id=inventory_id, need=need, quantity=quantity,
            before_percent=need.ratio, after_percent=round(100 * (need.received + need.committed + granted[need.pk]) / need.quantity))
    audit(user, 'Tạo đề xuất phân bổ', notes=f'Đề xuất #{proposal.pk}; {sum(granted.values())} cuốn.')
    return proposal


def validate_proposal(proposal, lines):
    needs, inventories, snapshot = matching_data(proposal.snapshot['scope'])
    if snapshot != proposal.snapshot:
        raise ValidationError('Đề xuất đã lỗi thời vì kho hoặc nhu cầu thay đổi. Vui lòng tính lại.')
    inv_map = {i.pk: i for i in inventories}
    need_map = {n.pk: n for n in needs}
    totals_inv, totals_need = defaultdict(int), defaultdict(int)
    for line in lines:
        inv, need = inv_map.get(line.inventory_id), need_map.get(line.need_id)
        if not inv or not need or inv.book_id != need.book_id or inv.school_id == need.school_id:
            raise ValidationError('Nguồn và nhu cầu không phù hợp.')
        if line.quantity <= 0:
            raise ValidationError('Số lượng phân bổ phải lớn hơn 0.')
        totals_inv[inv.pk] += line.quantity
        totals_need[need.pk] += line.quantity
    if any(q > inv_map[pk].available for pk, q in totals_inv.items()):
        raise ValidationError('Phân bổ vượt số sách có thể cho mượn.')
    if any(q > need_map[pk].remaining for pk, q in totals_need.items()):
        raise ValidationError('Phân bổ vượt nhu cầu còn thiếu.')
    return inv_map, need_map, totals_inv, totals_need


@transaction.atomic
def edit_proposal(user, pk, quantities, reason):
    require_coordinator(user)
    proposal = Proposal.objects.get(pk=pk)
    if proposal.status != Proposal.Status.DRAFT:
        raise ValidationError('Đề xuất đã duyệt không thể sửa.')
    if not reason.strip():
        raise ValidationError('Hãy ghi lý do điều chỉnh đề xuất.')
    lines = list(proposal.lines.all())
    for line in lines:
        line.quantity = quantities.get(line.pk, line.quantity)
    _, needs, _, totals = validate_proposal(proposal, lines)
    for line in lines:
        need = needs[line.need_id]
        line.after_percent = round(100 * (need.received + need.committed + totals[need.pk]) / need.quantity)
        line.save(update_fields=['quantity', 'after_percent'])
    proposal.reason = reason
    proposal.save(update_fields=['reason'])
    audit(user, 'Điều chỉnh đề xuất', notes=f'Đề xuất #{pk}: {reason}')
    return proposal


@transaction.atomic
def approve_proposal(user, pk):
    require_coordinator(user)
    proposal = Proposal.objects.get(pk=pk)
    if proposal.status != Proposal.Status.DRAFT:
        raise ValidationError('Đề xuất đã được duyệt trước đó.')
    lines = list(proposal.lines.all())
    inv_map, need_map, inv_totals, need_totals = validate_proposal(proposal, lines)
    for pk, q in inv_totals.items():
        inv = inv_map[pk]
        inv.reserved += q
        inv.version += 1
        inv.save()
    for pk, q in need_totals.items():
        need = need_map[pk]
        need.committed += q
        need.version += 1
        need.save()
    loans = []
    for line in lines:
        loan = Loan.objects.create(inventory_id=line.inventory_id, need_id=line.need_id,
            proposal_line=line, quantity=line.quantity, return_by=need_map[line.need_id].return_by)
        audit(user, 'Duyệt và giữ chỗ', loan=loan, notes=proposal.reason)
        loans.append(loan)
    proposal.status = Proposal.Status.APPROVED
    proposal.save(update_fields=['status'])
    return loans


def available_actions(user, loan):
    sid = school_id(user)
    lender = sid is not None and sid == loan.inventory.school_id
    borrower = sid is not None and sid == loan.need.school_id
    participant = lender or borrower
    actions = []
    if loan.status == Loan.Status.PENDING and not loan.issue_open:
        if lender and not loan.lender_confirmed:
            actions.append(('confirm_lender', 'Đồng ý cho mượn'))
        if borrower and not loan.borrower_confirmed:
            actions.append(('confirm_borrower', 'Đồng ý mượn'))
        if participant:
            actions.append(('reject', 'Từ chối đề nghị'))
    if loan.status in [Loan.Status.PENDING, Loan.Status.READY] and (participant or coordinator(user)):
        actions.append(('cancel', 'Hủy phiếu'))
    if not loan.issue_open:
        if loan.status == Loan.Status.READY and lender:
            actions.append(('send', 'Xác nhận đã gửi đủ'))
        if loan.status == Loan.Status.SENT and borrower:
            actions.append(('receive', 'Xác nhận đã nhận đủ'))
        if loan.status == Loan.Status.BORROWED and borrower:
            actions.append(('return', 'Báo đã gửi trả đủ'))
        if loan.status == Loan.Status.RETURNING and lender:
            actions.append(('complete', 'Xác nhận nhận lại đủ'))
    if loan.status not in [Loan.Status.COMPLETED, Loan.Status.CANCELLED] and (participant or coordinator(user)):
        actions.append(('issue', 'Báo vấn đề'))
        if loan.issue_open and coordinator(user):
            actions.append(('resolve', 'Xác nhận vấn đề đã xử lý'))
    return actions


@transaction.atomic
def transition(user, pk, action, notes=''):
    loan = Loan.objects.select_related('inventory__school', 'need__school').get(pk=pk)
    sid = school_id(user)
    if not coordinator(user) and (sid is None or sid not in [loan.inventory.school_id, loan.need.school_id]):
        raise PermissionDenied
    allowed = dict(available_actions(user, loan))
    if action not in allowed:
        raise ValidationError('Thao tác không còn khả dụng hoặc bạn không có quyền xác nhận cho bên này.')
    if action in ['reject', 'cancel', 'issue', 'resolve'] and not notes.strip():
        raise ValidationError('Hãy ghi rõ lý do hoặc cách xử lý.')
    inv, need = loan.inventory, loan.need
    if action == 'confirm_lender':
        loan.lender_confirmed = True
    elif action == 'confirm_borrower':
        loan.borrower_confirmed = True
    elif action in ['reject', 'cancel']:
        loan.status = Loan.Status.CANCELLED
        inv.reserved -= loan.quantity
        need.committed -= loan.quantity
    elif action == 'send':
        loan.status = Loan.Status.SENT
        inv.reserved -= loan.quantity
        inv.lent += loan.quantity
    elif action == 'receive':
        loan.status = Loan.Status.BORROWED
        need.committed -= loan.quantity
        need.received += loan.quantity
        if need.received == need.quantity:
            need.status = Need.Status.FULFILLED
    elif action == 'return':
        loan.status = Loan.Status.RETURNING
    elif action == 'complete':
        loan.status = Loan.Status.COMPLETED
        inv.lent -= loan.quantity
    elif action == 'issue':
        loan.issue_open = True
    elif action == 'resolve':
        loan.issue_open = False
    if loan.status == Loan.Status.PENDING and loan.lender_confirmed and loan.borrower_confirmed:
        loan.status = Loan.Status.READY
    if action in ['reject', 'cancel', 'send', 'complete']:
        inv.version += 1
        inv.full_clean()
        inv.save()
    if action in ['reject', 'cancel', 'receive']:
        need.version += 1
        need.full_clean()
        need.save()
    loan.full_clean()
    loan.save()
    audit(user, allowed[action], loan=loan, notes=notes)
    return loan
