import inspect
import os
import re
from importlib import import_module

from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admindocs import utils
from django.core.exceptions import ImproperlyConfigured, ViewDoesNotExist
from django.db import models
from django.http import Http404
from django.template.engine import Engine
from django.urls import get_mod_func, get_resolver, get_urlconf, reverse
from django.utils import six
from django.utils.decorators import method_decorator
from django.utils.inspect import (
    func_accepts_kwargs, func_accepts_var_args, func_has_no_args,
    get_func_full_args,
)
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView

# Exclude methods starting with these strings from documentation
MODEL_METHODS_EXCLUDE = ('_', 'add_', 'delete', 'save', 'set_')


class BaseAdminDocsView(TemplateView):
    """
    Base view for admindocs views.
    """
    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        if not utils.docutils_is_available:
            # Display an error message for people without docutils
            self.template_name = 'admin_doc/missing_docutils.html'
            return self.render_to_response(admin.site.each_context(request))
        return super(BaseAdminDocsView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs.update({'root_path': reverse('admin:index')})
        kwargs.update(admin.site.each_context(self.request))
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
        tags = []
        try:
            engine = Engine.get_default()
        except ImproperlyConfigured:
            # Non-trivial TEMPLATES settings aren't supported (#24125).
            pass
        else:
            app_libs = sorted(engine.template_libraries.items())
            builtin_libs = [('', lib) for lib in engine.template_builtins]
            for module_name, library in builtin_libs + app_libs:
                for tag_name, tag_func in library.tags.items():
                    title, body, metadata = utils.parse_docstring(tag_func.__doc__)
                    if title:
                        title = utils.parse_rst(title, 'tag', _('tag:') + tag_name)
                    if body:
                        body = utils.parse_rst(body, 'tag', _('tag:') + tag_name)
                    for key in metadata:
                        metadata[key] = utils.parse_rst(metadata[key], 'tag', _('tag:') + tag_name)
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
        filters = []
        try:
            engine = Engine.get_default()
        except ImproperlyConfigured:
            # Non-trivial TEMPLATES settings aren't supported (#24125).
            pass
        else:
            app_libs = sorted(engine.template_libraries.items())
            builtin_libs = [('', lib) for lib in engine.template_builtins]
            for module_name, library in builtin_libs + app_libs:
                for filter_name, filter_func in library.filters.items():
                    title, body, metadata = utils.parse_docstring(filter_func.__doc__)
                    if title:
                        title = utils.parse_rst(title, 'filter', _('filter:') + filter_name)
                    if body:
                        body = utils.parse_rst(body, 'filter', _('filter:') + filter_name)
                    for key in metadata:
                        metadata[key] = utils.parse_rst(metadata[key], 'filter', _('filter:') + filter_name)
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

    @staticmethod
    def _get_full_name(func):
        mod_name = func.__module__
        if six.PY3:
            return '%s.%s' % (mod_name, func.__qualname__)
        else:
            # PY2 does not support __qualname__
            func_name = getattr(func, '__name__', func.__class__.__name__)
            return '%s.%s' % (mod_name, func_name)

    def get_context_data(self, **kwargs):
        views = []
        urlconf = import_module(settings.ROOT_URLCONF)
        view_functions = extract_views_from_urlpatterns(urlconf.urlpatterns)
        for (func, regex, namespace, name) in view_functions:
            views.append({
                'full_name': self._get_full_name(func),
                'url': simplify_regex(regex),
                'url_name': ':'.join((namespace or []) + (name and [name] or [])),
                'namespace': ':'.join((namespace or [])),
                'name': name,
            })
        kwargs.update({'views': views})
        return super(ViewIndexView, self).get_context_data(**kwargs)


class ViewDetailView(BaseAdminDocsView):
    template_name = 'admin_doc/view_detail.html'

    @staticmethod
    def _get_view_func(view):
        urlconf = get_urlconf()
        if get_resolver(urlconf)._is_callback(view):
            mod, func = get_mod_func(view)
            try:
                # Separate the module and function, e.g.
                # 'mymodule.views.myview' -> 'mymodule.views', 'myview').
                return getattr(import_module(mod), func)
            except ImportError:
                # Import may fail because view contains a class name, e.g.
                # 'mymodule.views.ViewContainer.my_view', so mod takes the form
                # 'mymodule.views.ViewContainer'. Parse it again to separate
                # the module and class.
                mod, klass = get_mod_func(mod)
                return getattr(getattr(import_module(mod), klass), func)
            except AttributeError:
                # PY2 generates incorrect paths for views that are methods,
                # e.g. 'mymodule.views.ViewContainer.my_view' will be
                # listed as 'mymodule.views.my_view' because the class name
                # can't be detected. This causes an AttributeError when
                # trying to resolve the view.
                return None

    def get_context_data(self, **kwargs):
        view = self.kwargs['view']
        view_func = self._get_view_func(view)
        if view_func is None:
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
        model_name = self.kwargs['model_name']
        # Get the model class.
        try:
            app_config = apps.get_app_config(self.kwargs['app_label'])
        except LookupError:
            raise Http404(_("App %(app_label)r not found") % self.kwargs)
        try:
            model = app_config.get_model(model_name)
        except LookupError:
            raise Http404(_("Model %(model_name)r not found in app %(app_label)r") % self.kwargs)

        opts = model._meta

        title, body, metadata = utils.parse_docstring(model.__doc__)
        if title:
            title = utils.parse_rst(title, 'model', _('model:') + model_name)
        if body:
            body = utils.parse_rst(body, 'model', _('model:') + model_name)

        # Gather fields/field descriptions.
        fields = []
        for field in opts.fields:
            # ForeignKey is a special case since the field will actually be a
            # descriptor that returns the other object
            if isinstance(field, models.ForeignKey):
                data_type = field.remote_field.model.__name__
                app_label = field.remote_field.model._meta.app_label
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
                'verbose': verbose or '',
                'help_text': field.help_text,
            })

        # Gather many-to-many fields.
        for field in opts.many_to_many:
            data_type = field.remote_field.model.__name__
            app_label = field.remote_field.model._meta.app_label
            verbose = _("related `%(app_label)s.%(object_name)s` objects") % {
                'app_label': app_label,
                'object_name': data_type,
            }
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

        methods = []
        # Gather model methods.
        for func_name, func in model.__dict__.items():
            if inspect.isfunction(func):
                try:
                    for exclude in MODEL_METHODS_EXCLUDE:
                        if func_name.startswith(exclude):
                            raise StopIteration
                except StopIteration:
                    continue
                verbose = func.__doc__
                if verbose:
                    verbose = utils.parse_rst(utils.trim_docstring(verbose), 'model', _('model:') + opts.model_name)
                # If a method has no arguments, show it as a 'field', otherwise
                # as a 'method with arguments'.
                if func_has_no_args(func) and not func_accepts_kwargs(func) and not func_accepts_var_args(func):
                    fields.append({
                        'name': func_name,
                        'data_type': get_return_data_type(func_name),
                        'verbose': verbose or '',
                    })
                else:
                    arguments = get_func_full_args(func)
                    print_arguments = arguments
                    # Join arguments with ', ' and in case of default value,
                    # join it with '='. Use repr() so that strings will be
                    # correctly displayed.
                    print_arguments = ', '.join([
                        '='.join(list(arg_el[:1]) + [repr(el) for el in arg_el[1:]])
                        for arg_el in arguments
                    ])
                    methods.append({
                        'name': func_name,
                        'arguments': print_arguments,
                        'verbose': verbose or '',
                    })

        # Gather related objects
        for rel in opts.related_objects:
            verbose = _("related `%(app_label)s.%(object_name)s` objects") % {
                'app_label': rel.related_model._meta.app_label,
                'object_name': rel.related_model._meta.object_name,
            }
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
            'summary': title,
            'description': body,
            'fields': fields,
            'methods': methods,
        })
        return super(ModelDetailView, self).get_context_data(**kwargs)


class TemplateDetailView(BaseAdminDocsView):
    template_name = 'admin_doc/template_detail.html'

    def get_context_data(self, **kwargs):
        template = self.kwargs['template']
        templates = []
        try:
            default_engine = Engine.get_default()
        except ImproperlyConfigured:
            # Non-trivial TEMPLATES settings aren't supported (#24125).
            pass
        else:
            # This doesn't account for template loaders (#24128).
            for index, directory in enumerate(default_engine.dirs):
                template_file = os.path.join(directory, template)
                templates.append({
                    'file': template_file,
                    'exists': os.path.exists(template_file),
                    'contents': lambda: open(template_file).read() if os.path.exists(template_file) else '',
                    'order': index,
                })
        kwargs.update({
            'name': template,
            'templates': templates,
        })
        return super(TemplateDetailView, self).get_context_data(**kwargs)


####################
# Helper functions #
####################


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
