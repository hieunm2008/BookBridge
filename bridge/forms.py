from django import forms
from .access import coordinator, school_id
from .models import Book, Inventory, Need, School


class ScopedForm(forms.Form):
    school = forms.ModelChoiceField(label='Điểm trường', queryset=School.objects.all())
    book = forms.ModelChoiceField(label='Đầu sách', queryset=Book.objects.all(), help_text='Kiểm tra đúng lớp, bộ sách và năm xuất bản.')
    version = forms.IntegerField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, user, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        if not coordinator(user):
            self.fields['school'].queryset = School.objects.filter(pk=school_id(user))
            self.fields['school'].initial = school_id(user)
            self.fields['school'].disabled = True
        if instance:
            for name in self.fields:
                if hasattr(instance, name):
                    self.initial[name] = getattr(instance, name)
            self.fields['school'].disabled = True
            self.fields['book'].disabled = True
            self.initial['school'] = instance.school_id
            self.initial['book'] = instance.book_id


class InventoryForm(ScopedForm):
    owned = forms.IntegerField(label='Số sách sở hữu', min_value=0, widget=forms.NumberInput(attrs={'data-owned': ''}))
    internal = forms.IntegerField(label='Số giữ lại dùng nội bộ', min_value=0, widget=forms.NumberInput(attrs={'data-internal': ''}))
    reason = forms.CharField(label='Lý do điều chỉnh', required=False, widget=forms.Textarea(attrs={'rows': 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['reason'].required = True


class NeedForm(ScopedForm):
    quantity = forms.IntegerField(label='Số cuốn cần bổ sung', min_value=1)
    needed_by = forms.DateField(label='Ngày cần sách', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    return_by = forms.DateField(label='Ngày dự kiến trả', widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date'}))
    notes = forms.CharField(label='Ghi chú', required=False, widget=forms.Textarea(attrs={'rows': 3}))

    def clean(self):
        data = super().clean()
        if data.get('needed_by') and data.get('return_by') and data['return_by'] < data['needed_by']:
            self.add_error('return_by', 'Ngày trả phải bằng hoặc sau ngày cần sách.')
        return data
