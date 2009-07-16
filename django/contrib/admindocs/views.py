from django import template, templatetags
from django.template import RequestContext
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.shortcuts import render_to_response
from django.core.exceptions import ImproperlyConfigured, ViewDoesNotExist
from django.http import Http404
from django.core import urlresolvers
from django.contrib.admindocs import utils
from django.contrib.sites.models import Site
from django.utils.importlib import import_module
from django.utils.translation import ugettext as _
from django.utils.safestring import mark_safe
import inspect, os, re

# Exclude methods starting with these strings from documentation
MODEL_METHODS_EXCLUDE = ('_', 'add_', 'delete', 'save', 'set_')

class GenericSite(object):
    domain = 'example.com'
    name = 'my site'

def get_root_path():
    try:
        return urlresolvers.reverse('admin:index')
    except urlresolvers.NoReverseMatch:
        from django.contrib import admin
        try:
            return urlresolvers.reverse(admin.site.root, args=[''])
        except urlresolvers.NoReverseMatch:
            return getattr(settings, "ADMIN_SITE_ROOT_URL", "/admin/")

def doc_index(request):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)
    return render_to_response('admin_doc/index.html', {
        'root_path': get_root_path(),
    }, context_instance=RequestContext(request))
doc_index = staff_member_required(doc_index)

def bookmarklets(request):
    admin_root = get_root_path()
    return render_to_response('admin_doc/bookmarklets.html', {
        'root_path': admin_root,
        'admin_url': mark_safe("%s://%s%s" % (request.is_secure() and 'https' or 'http', request.get_host(), admin_root)),
    }, context_instance=RequestContext(request))
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
                title = utils.parse_rst(title, 'tag', _('tag:') + tag_name)
            if body:
                body = utils.parse_rst(body, 'tag', _('tag:') + tag_name)
            for key in metadata:
                metadata[key] = utils.parse_rst(metadata[key], 'tag', _('tag:') + tag_name)
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
    return render_to_response('admin_doc/template_tag_index.html', {
        'root_path': get_root_path(),
        'tags': tags
    }, context_instance=RequestContext(request))
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
                title = utils.parse_rst(title, 'filter', _('filter:') + filter_name)
            if body:
                body = utils.parse_rst(body, 'filter', _('filter:') + filter_name)
            for key in metadata:
                metadata[key] = utils.parse_rst(metadata[key], 'filter', _('filter:') + filter_name)
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
    return render_to_response('admin_doc/template_filter_index.html', {
        'root_path': get_root_path(),
        'filters': filters
    }, context_instance=RequestContext(request))
template_filter_index = staff_member_required(template_filter_index)

def view_index(request):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)

    if settings.ADMIN_FOR:
        settings_modules = [import_module(m) for m in settings.ADMIN_FOR]
    else:
        settings_modules = [settings]

    views = []
    for settings_mod in settings_modules:
        urlconf = import_module(settings_mod.ROOT_URLCONF)
        view_functions = extract_views_from_urlpatterns(urlconf.urlpatterns)
        if Site._meta.installed:
            site_obj = Site.objects.get(pk=settings_mod.SITE_ID)
        else:
            site_obj = GenericSite()
        for (func, regex) in view_functions:
            views.append({
                'name': getattr(func, '__name__', func.__class__.__name__),
                'module': func.__module__,
                'site_id': settings_mod.SITE_ID,
                'site': site_obj,
                'url': simplify_regex(regex),
            })
    return render_to_response('admin_doc/view_index.html', {
        'root_path': get_root_path(),
        'views': views
    }, context_instance=RequestContext(request))
view_index = staff_member_required(view_index)

def view_detail(request, view):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)

    mod, func = urlresolvers.get_mod_func(view)
    try:
        view_func = getattr(import_module(mod), func)
    except (ImportError, AttributeError):
        raise Http404
    title, body, metadata = utils.parse_docstring(view_func.__doc__)
    if title:
        title = utils.parse_rst(title, 'view', _('view:') + view)
    if body:
        body = utils.parse_rst(body, 'view', _('view:') + view)
    for key in metadata:
        metadata[key] = utils.parse_rst(metadata[key], 'model', _('view:') + view)
    return render_to_response('admin_doc/view_detail.html', {
        'root_path': get_root_path(),
        'name': view,
        'summary': title,
        'body': body,
        'meta': metadata,
    }, context_instance=RequestContext(request))
view_detail = staff_member_required(view_detail)

def model_index(request):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)
    m_list = [m._meta for m in models.get_models()]
    return render_to_response('admin_doc/model_index.html', {
        'root_path': get_root_path(),
        'models': m_list
    }, context_instance=RequestContext(request))
model_index = staff_member_required(model_index)

def model_detail(request, app_label, model_name):
    if not utils.docutils_is_available:
        return missing_docutils_page(request)

    # Get the model class.
    try:
        app_mod = models.get_app(app_label)
    except ImproperlyConfigured:
        raise Http404, _("App %r not found") % app_label
    model = None
    for m in models.get_models(app_mod):
        if m._meta.object_name.lower() == model_name:
            model = m
            break
    if model is None:
        raise Http404, _("Model %(model_name)r not found in app %(app_label)r") % {'model_name': model_name, 'app_label': app_label}

    opts = model._meta

    # Gather fields/field descriptions.
    fields = []
    for field in opts.fields:
        # ForeignKey is a special case since the field will actually be a
        # descriptor that returns the other object
        if isinstance(field, models.ForeignKey):
            data_type = related_object_name = field.rel.to.__name__
            app_label = field.rel.to._meta.app_label
            verbose = utils.parse_rst((_("the related `%(app_label)s.%(data_type)s` object")  % {'app_label': app_label, 'data_type': data_type}), 'model', _('model:') + data_type)
        else:
            data_type = get_readable_field_data_type(field)
            verbose = field.verbose_name
        fields.append({
            'name': field.name,
            'data_type': data_type,
            'verbose': verbose,
            'help_text': field.help_text,
        })

    # Gather many-to-many fields.
    for field in opts.many_to_many:
        data_type = related_object_name = field.rel.to.__name__
        app_label = field.rel.to._meta.app_label
        verbose = _("related `%(app_label)s.%(object_name)s` objects") % {'app_label': app_label, 'object_name': data_type}
        fields.append({
            'name': "%s.all" % field.name,
            "data_type": 'List',
            'verbose': utils.parse_rst(_("all %s") % verbose , 'model', _('model:') + opts.module_name),
        })
        fields.append({
            'name'      : "%s.count" % field.name,
            'data_type' : 'Integer',
            'verbose'   : utils.parse_rst(_("number of %s") % verbose , 'model', _('model:') + opts.module_name),
        })

    # Gather model methods.
    for func_name, func in model.__dict__.items():
        if (inspect.isfunction(func) and len(inspect.getargspec(func)[0]) == 1):
            try:
                for exclude in MODEL_METHODS_EXCLUDE:
                    if func_name.startswith(exclude):
                        raise StopIteration
            except StopIteration:
                continue
            verbose = func.__doc__
            if verbose:
                verbose = utils.parse_rst(utils.trim_docstring(verbose), 'model', _('model:') + opts.module_name)
            fields.append({
                'name': func_name,
                'data_type': get_return_data_type(func_name),
                'verbose': verbose,
            })

    # Gather related objects
    for rel in opts.get_all_related_objects() + opts.get_all_related_many_to_many_objects():
        verbose = _("related `%(app_label)s.%(object_name)s` objects") % {'app_label': rel.opts.app_label, 'object_name': rel.opts.object_name}
        accessor = rel.get_accessor_name()
        fields.append({
            'name'      : "%s.all" % accessor,
            'data_type' : 'List',
            'verbose'   : utils.parse_rst(_("all %s") % verbose , 'model', _('model:') + opts.module_name),
        })
        fields.append({
            'name'      : "%s.count" % accessor,
            'data_type' : 'Integer',
            'verbose'   : utils.parse_rst(_("number of %s") % verbose , 'model', _('model:') + opts.module_name),
        })
    return render_to_response('admin_doc/model_detail.html', {
        'root_path': get_root_path(),
        'name': '%s.%s' % (opts.app_label, opts.object_name),
        'summary': _("Fields on %s objects") % opts.object_name,
        'description': model.__doc__,
        'fields': fields,
    }, context_instance=RequestContext(request))
model_detail = staff_member_required(model_detail)

def template_detail(request, template):
    templates = []
    for site_settings_module in settings.ADMIN_FOR:
        settings_mod = import_module(site_settings_module)
        if Site._meta.installed:
            site_obj = Site.objects.get(pk=settings_mod.SITE_ID)
        else:
            site_obj = GenericSite()
        for dir in settings_mod.TEMPLATE_DIRS:
            template_file = os.path.join(dir, template)
            templates.append({
                'file': template_file,
                'exists': os.path.exists(template_file),
                'contents': lambda: os.path.exists(template_file) and open(template_file).read() or '',
                'site_id': settings_mod.SITE_ID,
                'site': site_obj,
                'order': list(settings_mod.TEMPLATE_DIRS).index(dir),
            })
    return render_to_response('admin_doc/template_detail.html', {
        'root_path': get_root_path(),
        'name': template,
        'templates': templates,
    }, context_instance=RequestContext(request))
template_detail = staff_member_required(template_detail)

####################
# Helper functions #
####################

def missing_docutils_page(request):
    """Display an error message for people without docutils"""
    return render_to_response('admin_doc/missing_docutils.html')

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
    'CharField'                 : _('String (up to %(max_length)s)'),
    'CommaSeparatedIntegerField': _('Comma-separated integers'),
    'DateField'                 : _('Date (without time)'),
    'DateTimeField'             : _('Date (with time)'),
    'DecimalField'              : _('Decimal number'),
    'EmailField'                : _('E-mail address'),
    'FileField'                 : _('File path'),
    'FilePathField'             : _('File path'),
    'FloatField'                : _('Floating point number'),
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
    'SlugField'                 : _('String (up to %(max_length)s)'),
    'SmallIntegerField'         : _('Integer'),
    'TextField'                 : _('Text'),
    'TimeField'                 : _('Time'),
    'URLField'                  : _('URL'),
    'USStateField'              : _('U.S. state (two uppercase letters)'),
    'XMLField'                  : _('XML text'),
}

def get_readable_field_data_type(field):
    return DATA_TYPE_MAPPING[field.get_internal_type()] % field.__dict__

def extract_views_from_urlpatterns(urlpatterns, base=''):
    """
    Return a list of views from a list of urlpatterns.

    Each object in the returned list is a two-tuple: (view_func, regex)
    """
    views = []
    for p in urlpatterns:
        if hasattr(p, '_get_callback'):
            try:
                views.append((p._get_callback(), base + p.regex.pattern))
            except ViewDoesNotExist:
                continue
        elif hasattr(p, '_get_url_patterns'):
            try:
                patterns = p.url_patterns
            except ImportError:
                continue
            views.extend(extract_views_from_urlpatterns(patterns, base + p.regex.pattern))
        else:
            raise TypeError, _("%s does not appear to be a urlpattern object") % p
    return views

named_group_matcher = re.compile(r'\(\?P(<\w+>).+?\)')
non_named_group_matcher = re.compile(r'\(.*?\)')

def simplify_regex(pattern):
    """
    Clean up urlpattern regexes into something somewhat readable by Mere Humans:
    turns something like "^(?P<sport_slug>\w+)/athletes/(?P<athlete_slug>\w+)/$"
    into "<sport_slug>/athletes/<athlete_slug>/"
    """
    # handle named groups first
    pattern = named_group_matcher.sub(lambda m: m.group(1), pattern)

    # handle non-named groups
    pattern = non_named_group_matcher.sub("<var>", pattern)

    # clean up any outstanding regex-y characters.
    pattern = pattern.replace('^', '').replace('$', '').replace('?', '').replace('//', '/').replace('\\', '')
    if not pattern.startswith('/'):
        pattern = '/' + pattern
    return pattern
