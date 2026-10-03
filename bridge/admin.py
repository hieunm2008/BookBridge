from django.contrib import admin
from .models import Audit, Book, Inventory, Loan, Need, Profile, Proposal, ProposalLine, School

admin.site.site_header = 'BookBridge · Quản trị'
admin.site.site_title = 'BookBridge'
admin.site.index_title = 'Quản lý danh mục và tài khoản'

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'province', 'locality', 'contact_name']
    search_fields = ['code', 'name']
    list_filter = ['province']

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['title', 'grade', 'series', 'year', 'kind']
    search_fields = ['title', 'series']
    list_filter = ['grade', 'kind', 'year']

    def get_readonly_fields(self, request, obj=None):
        if obj and (Inventory.objects.filter(book=obj).exists() or Need.objects.filter(book=obj).exists()):
            return ['title', 'subject', 'grade', 'series', 'publisher', 'year', 'kind']
        return []

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role', 'school']
    list_filter = ['role']

class ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Inventory)
class InventoryAdmin(ReadOnlyAdmin):
    list_display = ['school', 'book', 'owned', 'internal', 'reserved', 'lent']

@admin.register(Need)
class NeedAdmin(ReadOnlyAdmin):
    list_display = ['school', 'book', 'quantity', 'received', 'committed', 'status']

@admin.register(Loan)
class LoanAdmin(ReadOnlyAdmin):
    list_display = ['code', 'quantity', 'status', 'return_by', 'issue_open']

@admin.register(Audit)
class AuditAdmin(ReadOnlyAdmin):
    list_display = ['created_at', 'actor', 'action', 'loan', 'inventory', 'need']

admin.site.register(Proposal, ReadOnlyAdmin)
admin.site.register(ProposalLine, ReadOnlyAdmin)
