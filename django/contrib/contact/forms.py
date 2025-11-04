from django import forms
from django.contrib.contact.models import ContactMessage
from django.utils.translation import gettext_lazy as _


class ContactForm(forms.ModelForm):
    """
    Form for submitting contact messages.
    """

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]
        widgets = {
            "message": forms.Textarea(attrs={"rows": 5}),
        }
        help_texts = {
            "name": _("Please enter your full name."),
            "email": _("We'll never share your email with anyone else."),
            "message": _("Please provide as much detail as possible."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields required
        for field in self.fields.values():
            field.required = True
