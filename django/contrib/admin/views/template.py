from django import template, forms
from django.contrib.admin.views.decorators import staff_member_required
from django.template import loader
from django.shortcuts import render_to_response
from django.contrib.sites.models import Site
from django.conf import settings
from django.utils.translation import ugettext_lazy as _


def template_validator(request):
    """
    Displays the template validator form, which finds and displays template
    syntax errors.
    """
    # get a dict of {site_id : settings_module} for the validator
    settings_modules = {}
    for mod in settings.ADMIN_FOR:
        settings_module = __import__(mod, {}, {}, [''])
        settings_modules[settings_module.SITE_ID] = settings_module
    site_list = Site.objects.in_bulk(settings_modules.keys()).values()
    if request.POST:
        form = TemplateValidatorForm(settings_modules, site_list,
                                     data=request.POST)
        if form.is_valid():
            request.user.message_set.create(message='The template is valid.')
    else:
        form = TemplateValidatorForm(settings_modules, site_list)
    return render_to_response('admin/template_validator.html', {
        'title': 'Template validator',
        'form': form,
    }, context_instance=template.RequestContext(request))
template_validator = staff_member_required(template_validator)


class TemplateValidatorForm(forms.Form):
    site = forms.ChoiceField(_('site'))
    template = forms.CharField(
        _('template'), widget=forms.Textarea({'rows': 25, 'cols': 80}))

    def __init__(self, settings_modules, site_list, *args, **kwargs):
        self.settings_modules = settings_modules
        super(TemplateValidatorForm, self).__init__(*args, **kwargs)
        self.fields['site'].choices = [(s.id, s.name) for s in site_list]

    def clean_template(self):
        # Get the settings module. If the site isn't set, we don't raise an
        # error since the site field will.
        try:
            site_id = int(self.cleaned_data.get('site', None))
        except (ValueError, TypeError):
            return
        settings_module = self.settings_modules.get(site_id, None)
        if settings_module is None:
            return

        # So that inheritance works in the site's context, register a new
        # function for "extends" that uses the site's TEMPLATE_DIRS instead.
        def new_do_extends(parser, token):
            node = loader.do_extends(parser, token)
            node.template_dirs = settings_module.TEMPLATE_DIRS
            return node
        register = template.Library()
        register.tag('extends', new_do_extends)
        template.builtins.append(register)

        # Now validate the template using the new TEMPLATE_DIRS, making sure to
        # reset the extends function in any case.
        error = None
        template_string = self.cleaned_data['template']
        try:
            tmpl = loader.get_template_from_string(template_string)
            tmpl.render(template.Context({}))
        except template.TemplateSyntaxError, e:
            error = e
        template.builtins.remove(register)
        if error:
            raise forms.ValidationError, e.args
