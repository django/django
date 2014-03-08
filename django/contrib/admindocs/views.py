from importlib import import_module
import inspect
import os
import re
import warnings

from django import template
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.db import models
from django.core.exceptions import ViewDoesNotExist
from django.http import Http404
from django.core import urlresolvers
from django.contrib.admindocs import utils
from django.utils.decorators import method_decorator
from django.utils.deprecation import RemovedInDjango18Warning
from django.utils._os import upath
from django.utils import six
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView

# Exclude methods starting with these strings from documentation
MODEL_METHODS_EXCLUDE = ('_', 'add_', 'delete', 'save', 'set_')

if getattr(settings, 'ADMIN_FOR', None):
    warnings.warn('The ADMIN_FOR setting has been removed, you can remove '
                  'this setting from your configuration.', RemovedInDjango18Warning,
                  stacklevel=2)


class BaseAdminDocsView(TemplateView):
    """
    Base view for admindocs views.
    """
    @method_decorator(staff_member_required)
    def dispatch(self, *args, **kwargs):
        if not utils.docutils_is_available:
            # Display an error message for people without docutils
            self.template_name = 'admin_doc/missing_docutils.html'
            return self.render_to_response(admin.site.each_context())
        return super(BaseAdminDocsView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs.update({'root_path': urlresolvers.reverse('admin:index')})
        kwargs.update(admin.site.each_context())
        return super(BaseAdminDocsView, self).get_context_data(**kwargs)


class BookmarkletsView(BaseAdminDocsView):
    template_name = 'admin_doc/bookmarklets.html'

    def get_context_data(self, **kwargs):
        context = super(BookmarkletsView, self).get_context_data(**kwargs)
        context.update({
            'admin_url': "%s://%s%s" % (
                self.request.scheme, self.request.get_host(), context['root_path'])
        })
        return context


class TemplateTagIndexView(BaseAdminDocsView):
    template_name = 'admin_doc/template_tag_index.html'

    def get_context_data(self, **kwargs):
        load_all_installed_template_libraries()

        tags = []
        app_libs = list(six.iteritems(template.libraries))
        builtin_libs = [(None, lib) for lib in template.builtins]
        for module_name, library in builtin_libs + app_libs:
            for tag_name, tag_func in library.tags.items():
                title, body, metadata = utils.parse_docstring(tag_func.__doc__)
                if title:
                    title = utils.parse_rst(title, 'tag', _('tag:') + tag_name)
                if body:
                    body = utils.parse_rst(body, 'tag', _('tag:') + tag_name)
                for key in metadata:
                    metadata[key] = utils.parse_rst(metadata[key], 'tag', _('tag:') + tag_name)
                if library in template.builtins:
                    tag_library = ''
                else:
                    tag_library = module_name.split('.')[-1]
                tags.append({
                    'name': tag_name,
                    'title': title,
                    'body': body,
                    'meta': metadata,
                    'library': tag_library,
                })
        kwargs.update({'tags': tags})
        return super(TemplateTagIndexView, self).get_context_data(**kwargs)


class TemplateFilterIndexView(BaseAdminDocsView):
    template_name = 'admin_doc/template_filter_index.html'

    def get_context_data(self, **kwargs):
        load_all_installed_template_libraries()

        filters = []
        app_libs = list(six.iteritems(template.libraries))
        builtin_libs = [(None, lib) for lib in template.builtins]
        for module_name, library in builtin_libs + app_libs:
            for filter_name, filter_func in library.filters.items():
                title, body, metadata = utils.parse_docstring(filter_func.__doc__)
                if title:
                    title = utils.parse_rst(title, 'filter', _('filter:') + filter_name)
                if body:
                    body = utils.parse_rst(body, 'filter', _('filter:') + filter_name)
                for key in metadata:
                    metadata[key] = utils.parse_rst(metadata[key], 'filter', _('filter:') + filter_name)
                if library in template.builtins:
                    tag_library = ''
                else:
                    tag_library = module_name.split('.')[-1]
                filters.append({
                    'name': filter_name,
                    'title': title,
                    'body': body,
                    'meta': metadata,
                    'library': tag_library,
                })
        kwargs.update({'filters': filters})
        return super(TemplateFilterIndexView, self).get_context_data(**kwargs)


class ViewIndexView(BaseAdminDocsView):
    template_name = 'admin_doc/view_index.html'

    def get_context_data(self, **kwargs):
        views = []
        urlconf = import_module(settings.ROOT_URLCONF)
        view_functions = extract_views_from_urlpatterns(urlconf.urlpatterns)
        for (func, regex, namespace, name) in view_functions:
            views.append({
                'full_name': '%s.%s' % (func.__module__, getattr(func, '__name__', func.__class__.__name__)),
                'url': simplify_regex(regex),
                'url_name': ':'.join((namespace or []) + (name and [name] or [])),
                'namespace': ':'.join((namespace or [])),
                'name': name,
            })
        kwargs.update({'views': views})
        return super(ViewIndexView, self).get_context_data(**kwargs)


class ViewDetailView(BaseAdminDocsView):
    template_name = 'admin_doc/view_detail.html'

    def get_context_data(self, **kwargs):
        view = self.kwargs['view']
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
        kwargs.update({
            'name': view,
            'summary': title,
            'body': body,
            'meta': metadata,
        })
        return super(ViewDetailView, self).get_context_data(**kwargs)


class ModelIndexView(BaseAdminDocsView):
    template_name = 'admin_doc/model_index.html'

    def get_context_data(self, **kwargs):
        m_list = [m._meta for m in apps.get_models()]
        kwargs.update({'models': m_list})
        return super(ModelIndexView, self).get_context_data(**kwargs)


class ModelDetailView(BaseAdminDocsView):
    template_name = 'admin_doc/model_detail.html'

    def get_context_data(self, **kwargs):
        # Get the model class.
        try:
            app_config = apps.get_app_config(self.kwargs['app_label'])
        except LookupError:
            raise Http404(_("App %(app_label)r not found") % self.kwargs)
        try:
            model = app_config.get_model(self.kwargs['model_name'])
        except LookupError:
            raise Http404(_("Model %(model_name)r not found in app %(app_label)r") % self.kwargs)

        opts = model._meta

        # Gather fields/field descriptions.
        fields = []
        for field in opts.fields:
            # ForeignKey is a special case since the field will actually be a
            # descriptor that returns the other object
            if isinstance(field, models.ForeignKey):
                data_type = field.rel.to.__name__
                app_label = field.rel.to._meta.app_label
                verbose = utils.parse_rst(
                    (_("the related `%(app_label)s.%(data_type)s` object") % {
                        'app_label': app_label, 'data_type': data_type,
                    }),
                    'model',
                    _('model:') + data_type,
                )
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
            data_type = field.rel.to.__name__
            app_label = field.rel.to._meta.app_label
            verbose = _("related `%(app_label)s.%(object_name)s` objects") % {'app_label': app_label, 'object_name': data_type}
            fields.append({
                'name': "%s.all" % field.name,
                "data_type": 'List',
                'verbose': utils.parse_rst(_("all %s") % verbose, 'model', _('model:') + opts.model_name),
            })
            fields.append({
                'name': "%s.count" % field.name,
                'data_type': 'Integer',
                'verbose': utils.parse_rst(_("number of %s") % verbose, 'model', _('model:') + opts.model_name),
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
                    verbose = utils.parse_rst(utils.trim_docstring(verbose), 'model', _('model:') + opts.model_name)
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
                'name': "%s.all" % accessor,
                'data_type': 'List',
                'verbose': utils.parse_rst(_("all %s") % verbose, 'model', _('model:') + opts.model_name),
            })
            fields.append({
                'name': "%s.count" % accessor,
                'data_type': 'Integer',
                'verbose': utils.parse_rst(_("number of %s") % verbose, 'model', _('model:') + opts.model_name),
            })
        kwargs.update({
            'name': '%s.%s' % (opts.app_label, opts.object_name),
            # Translators: %s is an object type name
            'summary': _("Attributes on %s objects") % opts.object_name,
            'description': model.__doc__,
            'fields': fields,
        })
        return super(ModelDetailView, self).get_context_data(**kwargs)


class TemplateDetailView(BaseAdminDocsView):
    template_name = 'admin_doc/template_detail.html'

    def get_context_data(self, **kwargs):
        template = self.kwargs['template']
        templates = []
        for dir in settings.TEMPLATE_DIRS:
            template_file = os.path.join(dir, template)
            templates.append({
                'file': template_file,
                'exists': os.path.exists(template_file),
                'contents': lambda: open(template_file).read() if os.path.exists(template_file) else '',
                'order': list(settings.TEMPLATE_DIRS).index(dir),
            })
        kwargs.update({
            'name': template,
            'templates': templates,
        })
        return super(TemplateDetailView, self).get_context_data(**kwargs)


####################
# Helper functions #
####################

def load_all_installed_template_libraries():
    # Load/register all template tag libraries from installed apps.
    for module_name in template.get_templatetags_modules():
        mod = import_module(module_name)
        try:
            libraries = [
                os.path.splitext(p)[0]
                for p in os.listdir(os.path.dirname(upath(mod.__file__)))
                if p.endswith('.py') and p[0].isalpha()
            ]
        except OSError:
            libraries = []
        for library_name in libraries:
            try:
                template.get_library(library_name)
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


def get_readable_field_data_type(field):
    """Returns the description for a given field type, if it exists,
    Fields' descriptions can contain format strings, which will be interpolated
    against the values of field.__dict__ before being output."""

    return field.description % field.__dict__


def extract_views_from_urlpatterns(urlpatterns, base='', namespace=None):
    """
    Return a list of views from a list of urlpatterns.

    Each object in the returned list is a two-tuple: (view_func, regex)
    """
    views = []
    for p in urlpatterns:
        if hasattr(p, 'url_patterns'):
            try:
                patterns = p.url_patterns
            except ImportError:
                continue
            views.extend(extract_views_from_urlpatterns(
                patterns,
                base + p.regex.pattern,
                (namespace or []) + (p.namespace and [p.namespace] or [])
            ))
        elif hasattr(p, 'callback'):
            try:
                views.append((p.callback, base + p.regex.pattern,
                              namespace, p.name))
            except ViewDoesNotExist:
                continue
        else:
            raise TypeError(_("%s does not appear to be a urlpattern object") % p)
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
