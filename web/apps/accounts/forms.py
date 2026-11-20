from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from apps.jobs.models import Job

from .models import Profile, User


class BootstrapFormMixin:
    """Gắn class Bootstrap cho mọi widget để template chỉ cần render field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, (forms.CheckboxInput,)):
                widget.attrs.setdefault("class", "form-check-input")
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault("class", "form-select")
            else:
                widget.attrs.setdefault("class", "form-control")


class RegisterForm(BootstrapFormMixin, UserCreationForm):
    email = forms.EmailField(label="Email")

    class Meta:
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng.")
        return email


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    pass


class UserUpdateForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("Email này đã được sử dụng.")
        return email


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    preferred_work_mode = forms.ChoiceField(
        label="Hình thức làm việc",
        choices=[("", "Bất kỳ")] + list(Job.WorkMode.choices),
        required=False,
    )

    class Meta:
        model = Profile
        fields = ("desired_title", "skills", "years_experience", "preferred_city",
                  "preferred_work_mode", "min_salary", "bio")
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 4}),
            "years_experience": forms.NumberInput(attrs={"min": 0, "max": 40, "step": 0.5}),
            "min_salary": forms.NumberInput(attrs={"min": 0}),
        }

    def clean_years_experience(self):
        v = self.cleaned_data["years_experience"]
        if v is not None and v < 0:
            raise forms.ValidationError("Số năm kinh nghiệm không được âm.")
        return v
