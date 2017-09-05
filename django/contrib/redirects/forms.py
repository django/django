from django import forms
from django.apps import apps
from django.contrib import admin
from django.contrib.redirects.models import Redirect
from django.utils.translation import gettext_lazy as _


class RedirectForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if apps.is_installed('django.contrib.sites'):
            from django.contrib.sites.models import Site

            self.fields['site'] = forms.ModelChoiceField(
                queryset=Site.objects.all(),
                to_field_name='domain',
                empty_label='Any',
                widget=admin.widgets.AdminRadioSelect(attrs={
                    'class': admin.options.get_ul_class(admin.VERTICAL),
                }),
                label=_('Site'),
                help_text=_('If domain is not set, redirect from this site.'),
                required=False,
            )

    def save(self, commit=True):
        instance = super().save(commit=False)

        if apps.is_installed('django.contrib.sites') and not instance.domain:
            site = self.cleaned_data.get('site')

            instance.domain = getattr(site, 'domain', '')

        if commit:
            instance.save()

        return instance

    class Meta:
        model = Redirect
        fields = '__all__'
