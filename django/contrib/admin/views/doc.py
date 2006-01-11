from django import templatetags
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.core.extensions import DjangoContext, render_to_response
from django.core.exceptions import ViewDoesNotExist
from django.http import Http404
from django.core import template, urlresolvers
from django.contrib.admin import utils
from django.contrib.sites.models import Site
import inspect, os, re

# Exclude methods starting with these strings from documentation
MODEL_METHODS_EXCLUDE = ('_', 'add_', 'delete', 'save', 'set_')

def doc_index(request):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)
    return render_to_response('admin_doc/index', context_instance=DjangoContext(request))
doc_index = staff_member_required(doc_index)

def bookmarklets(request):
    # Hack! This couples this view to the URL it lives at.
    admin_root = request.path[:-len('doc/bookmarklets/')]
    return render_to_response('admin_doc/bookmarklets', {
        'admin_url': "%s://%s%s" % (os.environ.get('HTTPS') == 'on' and 'https' or 'http', request.META['HTTP_HOST'], admin_root),
    }, context_instance=DjangoContext(request))
bookmarklets = staff_member_required(bookmarklets)

def template_tag_index(request):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)

    load_all_installed_template_libraries()

    tags = []
    for module_name, library in template.libraries.items():
        for tag_name, tag_func in library.tags.items():
            title, body, metadata = utils.parse_docstring(tag_func.__doc__)
            if title:
                title = utils.parse_rst(title, 'tag', 'tag:' + tag_name)
            if body:
                body = utils.parse_rst(body, 'tag', 'tag:' + tag_name)
            for key in metadata:
                metadata[key] = utils.parse_rst(metadata[key], 'tag', 'tag:' + tag_name)
            if library in template.builtins:
                tag_library = None
            else:
                tag_library = module_name.split('.')[-1]
            tags.append({
                'name': tag_name,
                'title': title,
                'body': body,
                'meta': metadata,
                'library': tag_library,
            })

    return render_to_response('admin_doc/template_tag_index', {'tags': tags}, context_instance=DjangoContext(request))
template_tag_index = staff_member_required(template_tag_index)

def template_filter_index(request):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)

    load_all_installed_template_libraries()

    filters = []
    for module_name, library in template.libraries.items():
        for filter_name, filter_func in library.filters.items():
            title, body, metadata = utils.parse_docstring(filter_func.__doc__)
            if title:
                title = utils.parse_rst(title, 'filter', 'filter:' + filter_name)
            if body:
                body = utils.parse_rst(body, 'filter', 'filter:' + filter_name)
            for key in metadata:
                metadata[key] = utils.parse_rst(metadata[key], 'filter', 'filter:' + filter_name)
            if library in template.builtins:
                tag_library = None
            else:
                tag_library = module_name.split('.')[-1]
            filters.append({
                'name': filter_name,
                'title': title,
                'body': body,
                'meta': metadata,
                'library': tag_library,
            })
    return render_to_response('admin_doc/template_filter_index', {'filters': filters}, context_instance=DjangoContext(request))
template_filter_index = staff_member_required(template_filter_index)

def view_index(request):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)

    views = []
    for site_settings_module in settings.ADMIN_FOR:
        settings_mod = __import__(site_settings_module, '', '', [''])
        urlconf = __import__(settings_mod.ROOT_URLCONF, '', '', [''])
        view_functions = extract_views_from_urlpatterns(urlconf.urlpatterns)
        for (func, regex) in view_functions:
            views.append({
                'name': func.__name__,
                'module': func.__module__,
                'site_id': settings_mod.SITE_ID,
                'site': Site.objects.get_object(pk=settings_mod.SITE_ID),
                'url': simplify_regex(regex),
            })
    return render_to_response('admin_doc/view_index', {'views': views}, context_instance=DjangoContext(request))
view_index = staff_member_required(view_index)

def view_detail(request, view):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)

    mod, func = urlresolvers.get_mod_func(view)
    try:
        view_func = getattr(__import__(mod, '', '', ['']), func)
    except (ImportError, AttributeError):
        raise Http404
    title, body, metadata = utils.parse_docstring(view_func.__doc__)
    if title:
        title = utils.parse_rst(title, 'view', 'view:' + view)
    if body:
        body = utils.parse_rst(body, 'view', 'view:' + view)
    for key in metadata:
        metadata[key] = utils.parse_rst(metadata[key], 'model', 'view:' + view)
    return render_to_response('admin_doc/view_detail', {
        'name': view,
        'summary': title,
        'body': body,
        'meta': metadata,
    }, context_instance=DjangoContext(request))
view_detail = staff_member_required(view_detail)

def model_index(request):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)

    models = []
    for app in models.get_installed_model_modules():
        for model in app._MODELS:
            opts = model._meta
            models.append({
                'name': '%s.%s' % (opts.app_label, opts.module_name),
                'module': opts.app_label,
                'class': opts.module_name,
            })
    return render_to_response('admin_doc/model_index', {'models': models}, context_instance=DjangoContext(request))
model_index = staff_member_required(model_index)

def model_detail(request, model):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)

    try:
        model = models.get_app(model)
    except ImportError:
        raise Http404
    opts = model.Klass._meta

    # Gather fields/field descriptions
    fields = []
    for field in opts.fields:
        fields.append({
            'name': field.name,
            'data_type': get_readable_field_data_type(field),
            'verbose': field.verbose_name,
            'help': field.help_text,
        })
    for func_name, func in model.Klass.__dict__.items():
        if callable(func) and len(inspect.getargspec(func)[0]) == 0:
            try:
                for exclude in MODEL_METHODS_EXCLUDE:
                    if func_name.startswith(exclude):
                        raise StopIteration
            except StopIteration:
                continue
            verbose = func.__doc__
            if verbose:
                verbose = utils.parse_rst(utils.trim_docstring(verbose), 'model', 'model:' + opts.module_name)
            fields.append({
                'name': func_name,
                'data_type': get_return_data_type(func_name),
                'verbose': verbose,
            })
    return render_to_response('admin_doc/model_detail', {
        'name': '%s.%s' % (opts.app_label, opts.module_name),
        'summary': "Fields on %s objects" % opts.verbose_name,
        'fields': fields,
    }, context_instance=DjangoContext(request))
model_detail = staff_member_required(model_detail)

def template_detail(request, template):
    templates = []
    for site_settings_module in settings.ADMIN_FOR:
        settings_mod = __import__(site_settings_module, '', '', [''])
        for dir in settings_mod.TEMPLATE_DIRS:
            template_file = os.path.join(dir, "%s.html" % template)
            templates.append({
                'file': template_file,
                'exists': os.path.exists(template_file),
                'contents': lambda: os.path.exists(template_file) and open(template_file).read() or '',
                'site_id': settings_mod.SITE_ID,
                'site': Site.objects.get_object(pk=settings_mod.SITE_ID),
                'order': list(settings_mod.TEMPLATE_DIRS).index(dir),
            })
    return render_to_response('admin_doc/template_detail', {
        'name': template,
        'templates': templates,
    }, context_instance=DjangoContext(request))
template_detail = staff_member_required(template_detail)

####################
# Helper functions #
####################

def missing_docutils_page(request):
    """Display an error message for people without docutils"""
    return render_to_response('admin_doc/missing_docutils')

def load_all_installed_template_libraries():
    # Load/register all template tag libraries from installed apps.
    for e in templatetags.__path__:
        libraries = [os.path.splitext(p)[0] for p in os.listdir(e) if p.endswith('.py') and p[0].isalpha()]
        for library_name in libraries:
            try:
                lib = template.get_library("django.templatetags.%s" % library_name.split('.')[-1])
            except template.InvalidTemplateLibrary:
                pass

def get_return_data_type(func_name):
    """Return a somewhat-helpful data type given a function name"""
    if func_name.startswith('get_'):
        if func_name.endswith('_list'):
            return 'List'
        elif func_name.endswith('_count'):
            return 'Integer'
    return ''

# Maps Field objects to their human-readable data types, as strings.
# Column-type strings can contain format strings; they'll be interpolated
# against the values of Field.__dict__ before being output.
# If a column type is set to None, it won't be included in the output.
DATA_TYPE_MAPPING = {
    'AutoField'                 : _('Integer'),
    'BooleanField'              : _('Boolean (Either True or False)'),
    'CharField'                 : _('String (up to %(maxlength)s)'),
    'CommaSeparatedIntegerField': _('Comma-separated integers'),
    'DateField'                 : _('Date (without time)'),
    'DateTimeField'             : _('Date (with time)'),
    'EmailField'                : _('E-mail address'),
    'FileField'                 : _('File path'),
    'FloatField'                : _('Decimal number'),
    'ForeignKey'                : _('Integer'),
    'ImageField'                : _('File path'),
    'IntegerField'              : _('Integer'),
    'IPAddressField'            : _('IP address'),
    'ManyToManyField'           : '',
    'NullBooleanField'          : _('Boolean (Either True, False or None)'),
    'OneToOneField'             : _('Relation to parent model'),
    'PhoneNumberField'          : _('Phone number'),
    'PositiveIntegerField'      : _('Integer'),
    'PositiveSmallIntegerField' : _('Integer'),
    'SlugField'                 : _('String (up to 50)'),
    'SmallIntegerField'         : _('Integer'),
    'TextField'                 : _('Text'),
    'TimeField'                 : _('Time'),
    'URLField'                  : _('URL'),
    'USStateField'              : _('U.S. state (two uppercase letters)'),
    'XMLField'                  : _('XML text'),
}

def get_readable_field_data_type(field):
    # ForeignKey is a special case. Use the field type of the relation.
    if field.get_internal_type() == 'ForeignKey':
        field = field.rel.get_related_field()
    return DATA_TYPE_MAPPING[field.get_internal_type()] % field.__dict__

def extract_views_from_urlpatterns(urlpatterns, base=''):
    """
    Return a list of views from a list of urlpatterns.

    Each object in the returned list is a two-tuple: (view_func, regex)
    """
    views = []
    for p in urlpatterns:
        if hasattr(p, 'get_callback'):
            try:
                views.append((p.get_callback(), base + p.regex.pattern))
            except ViewDoesNotExist:
                continue
        elif hasattr(p, '_get_url_patterns'):
            views.extend(extract_views_from_urlpatterns(p.url_patterns, base + p.regex.pattern))
        else:
            raise TypeError, "%s does not appear to be a urlpattern object" % p
    return views

# Clean up urlpattern regexes into something somewhat readable by Mere Humans:
# turns something like "^(?P<sport_slug>\w+)/athletes/(?P<athlete_slug>\w+)/$"
# into "<sport_slug>/athletes/<athlete_slug>/"

named_group_matcher = re.compile(r'\(\?P(<\w+>).+?\)')

def simplify_regex(pattern):
    pattern = named_group_matcher.sub(lambda m: m.group(1), pattern)
    pattern = pattern.replace('^', '').replace('$', '').replace('?', '').replace('//', '/')
    if not pattern.startswith('/'):
        pattern = '/' + pattern
    return pattern
