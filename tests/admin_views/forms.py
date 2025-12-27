from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm, AdminPasswordChangeForm
from django.contrib.admin.helpers import ActionForm
from django.core.exceptions import ValidationError

from .models import Section


class CustomAdminAuthenticationForm(AdminAuthenticationForm):
    class Media:
        css = {"all": ("path/to/media.css",)}

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if username == "customform":
            raise ValidationError("custom form error")
        return username


class CustomAdminPasswordChangeForm(AdminPasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].label = "Custom old password label"


class MediaActionForm(ActionForm):
    class Media:
        js = ["path/to/media.js"]


class SectionFormWithOptgroups(forms.ModelForm):
    articles = forms.ChoiceField(
        choices=[
            ("Published", [("1", "Test Article")]),
            ("Draft", [("2", "Other Article")]),
        ],
        required=False,
    )

    class Meta:
        model = Section
        fields = ["name", "articles"]
