from mango.contrib.admin.forms import AdminAuthenticationForm
from mango.contrib.admin.helpers import ActionForm
from mango.core.exceptions import ValidationError


class CustomAdminAuthenticationForm(AdminAuthenticationForm):

    class Media:
        css = {'all': ('path/to/media.css',)}

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username == 'customform':
            raise ValidationError('custom form error')
        return username


class MediaActionForm(ActionForm):
    class Media:
        js = ['path/to/media.js']
