from django.core import formfields, template_loader, validators
from django.core import template
from django.core.extensions import DjangoContext, render_to_response
from django.models.core import sites
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
    return render_to_response('template_validator', {
        'title': 'Template validator',
        'form': formfields.FormWrapper(manipulator, new_data, errors),
    }, context_instance=DjangoContext(request))

class TemplateValidator(formfields.Manipulator):
    def __init__(self, settings_modules):
        self.settings_modules = settings_modules
        site_list = sites.get_in_bulk(settings_modules.keys()).values()
        self.fields = (
            formfields.SelectField('site', is_required=True, choices=[(s.id, s.name) for s in site_list]),
            formfields.LargeTextField('template', is_required=True, rows=25, validator_list=[self.isValidTemplate]),
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
        # for "extends" that uses the site's TEMPLATE_DIR instead
        def new_do_extends(parser, token):
            node = template_loader.do_extends(parser, token)
            node.template_dirs = settings_module.TEMPLATE_DIRS
            return node
        template.register_tag('extends', new_do_extends)

        # now validate the template using the new template dirs
        # making sure to reset the extends function in any case
        error = None
        try:
            tmpl = template_loader.get_template_from_string(field_data)
            tmpl.render(template.Context({}))
        except template.TemplateSyntaxError, e:
            error = e
        template.register_tag('extends', template_loader.do_extends)
        if error:
            raise validators.ValidationError, e.args
