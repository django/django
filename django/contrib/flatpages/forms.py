from django import forms
from django.utils.translation import ugettext_lazy as _
from django.contrib.flatpages.models import FlatPage

class FlatpageForm(forms.ModelForm):
    url = forms.RegexField(label=_("URL"), max_length=100, regex=r'^[-\w/\.~]+$',
        help_text = _("Example: '/about/contact/'. Make sure to have leading"
                      " and trailing slashes."),
        error_message = _("This value must contain only letters, numbers,"
                          " dots, underscores, dashes, slashes or tildes."))

    class Meta:
        model = FlatPage

    def clean(self):
        url = self.cleaned_data.get('url', None)
        sites = self.cleaned_data.get('sites', None)

        same_url = FlatPage.objects.filter(url=url)
        if self.instance.pk:
            same_url = same_url.exclude(pk=self.instance.pk)

        if same_url.filter(sites__in=sites).exists():
            for site in sites:
                if same_url.filter(sites=site).exists():
                    raise forms.ValidationError(
                        _('Flatpage with url %s already exists for site %s'
                          % (url, site)))

        return super(FlatpageForm, self).clean()
