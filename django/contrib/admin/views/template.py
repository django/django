from django.contrib.admin.views.decorators import staff_member_required
from django.core import validators
from django import template, forms
from django.template import loader
from django.template import RequestContext as Context
from django.core.extensions import render_to_response
from django.contrib.sites.models import Site
from django.conf import settings

def template_validator(request):
    """
    Displays the template validator form, which finds and displays template
    syntax errors.
    """
    # get a dict of {site_id : settings_module} for the validator
    settings_modules = {}
    for mod in settings.ADMIN_FOR:
        settings_module = __import__(mod, '', '', [''])
        settings_modules[settings_module.SITE_ID] = settings_module
    manipulator = TemplateValidator(settings_modules)
    new_data, errors = {}, {}
    if request.POST:
        new_data = request.POST.copy()
        errors = manipulator.get_validation_errors(new_data)
        if not errors:
            request.user.add_message('The template is valid.')
    return render_to_response('admin/template_validator', {
        'title': 'Template validator',
        'form': forms.FormWrapper(manipulator, new_data, errors),
    }, context_instance=RequestContext(request))
template_validator = staff_member_required(template_validator)

class TemplateValidator(forms.Manipulator):
    def __init__(self, settings_modules):
        self.settings_modules = settings_modules
        site_list = Site.objects.get_in_bulk(settings_modules.keys()).values()
        self.fields = (
            forms.SelectField('site', is_required=True, choices=[(s.id, s.name) for s in site_list]),
            forms.LargeTextField('template', is_required=True, rows=25, validator_list=[self.isValidTemplate]),
        )

    def isValidTemplate(self, field_data, all_data):
        # get the settings module
        # if the site isn't set, we don't raise an error since the site field will
        try:
            site_id = int(all_data.get('site', None))
        except (ValueError, TypeError):
            return
        settings_module = self.settings_modules.get(site_id, None)
        if settings_module is None:
            return

        # so that inheritance works in the site's context, register a new function
        # for "extends" that uses the site's TEMPLATE_DIRS instead.
        def new_do_extends(parser, token):
            node = loader.do_extends(parser, token)
            node.template_dirs = settings_module.TEMPLATE_DIRS
            return node
        register = template.Library()
        register.tag('extends', new_do_extends)
        template.builtins.append(register)

        # Now validate the template using the new template dirs
        # making sure to reset the extends function in any case.
        error = None
        try:
            tmpl = loader.get_template_from_string(field_data)
            tmpl.render(template.Context({}))
        except template.TemplateSyntaxError, e:
            error = e
        template.builtins.remove(register)
        if error:
            raise validators.ValidationError, e.args
