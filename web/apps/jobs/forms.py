from django import forms

from .models import Job


class JobFilterForm(forms.Form):
    SORT_CHOICES = [
        ("newest", "Hạn nộp xa nhất"),
        ("salary", "Lương cao nhất"),
        ("title", "Tên A-Z"),
    ]

    q = forms.CharField(label="Từ khóa", required=False,
                        widget=forms.TextInput(attrs={"placeholder": "Chức danh, công ty, kỹ năng..."}))
    city = forms.ChoiceField(label="Thành phố", required=False)
    skill = forms.CharField(label="Kỹ năng", required=False,
                            widget=forms.TextInput(attrs={"placeholder": "vd. Python", "list": "skill-options"}))
    work_mode = forms.ChoiceField(label="Hình thức", required=False,
                                  choices=[("", "Tất cả")] + list(Job.WorkMode.choices))
    employment_type = forms.ChoiceField(label="Loại hình", required=False,
                                        choices=[("", "Tất cả")] + list(Job.EmploymentType.choices))
    min_salary = forms.IntegerField(label="Lương từ (triệu)", required=False, min_value=0,
                                    widget=forms.NumberInput(attrs={"placeholder": "vd. 15"}))
    it_only = forms.BooleanField(label="Chỉ ngành IT", required=False, initial=True)
    active_only = forms.BooleanField(label="Chỉ tin còn hạn", required=False, initial=True)
    sort = forms.ChoiceField(label="Sắp xếp", required=False, choices=SORT_CHOICES)

    def __init__(self, *args, cities=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["city"].choices = [("", "Tất cả")] + [(c, c) for c in cities]
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs["class"] = "form-check-input"
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs["class"] = "form-select"
            else:
                field.widget.attrs["class"] = "form-control"
