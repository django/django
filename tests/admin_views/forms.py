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


class SectionFormWithObjectOptgroups(forms.ModelForm):
    """Form with model instances as optgroup keys (tests str() conversion)."""

    articles = forms.ChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Use Section instances as optgroup keys
        sections = Section.objects.all()[:2]
        if sections:
            self.fields["articles"].choices = [
                (sections[0], [("1", "Article 1")]),
                (
                    sections[1] if len(sections) > 1 else sections[0],
                    [("2", "Article 2")],
                ),
            ]

    class Meta:
        model = Section
        fields = ["name", "articles"]


class SectionFormWithDynamicOptgroups(forms.ModelForm):
    """
    Form where the field with optgroups is added dynamically in __init__.
    This tests that the implementation doesn't rely on accessing the
    uninstantiated form class's _meta or fields, which wouldn't work here.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dynamically add a field with optgroups after instantiation.
        self.fields["articles"] = forms.ChoiceField(
            choices=[
                ("Category A", [("1", "Item 1"), ("2", "Item 2")]),
                ("Category B", [("3", "Item 3"), ("4", "Item 4")]),
            ],
            required=False,
        )

    class Meta:
        model = Section
        fields = ["name"]
