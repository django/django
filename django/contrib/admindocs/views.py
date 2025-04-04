import inspect
from importlib import import_module
from inspect import cleandoc
from pathlib import Path

from django.apps import apps
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admindocs import utils
from django.contrib.admindocs.utils import (
    remove_non_capturing_groups,
    replace_metacharacters,
    replace_named_groups,
    replace_unnamed_groups,
)
from django.contrib.auth import get_permission_codename
from django.core.exceptions import (
    ImproperlyConfigured,
    PermissionDenied,
    ViewDoesNotExist,
)
from django.db import models
from django.http import Http404
from django.template.engine import Engine
from django.urls import get_mod_func, get_resolver, get_urlconf
from django.utils._os import safe_join
from django.utils.decorators import method_decorator
from django.utils.functional import cached_property
from django.utils.inspect import (
    func_accepts_kwargs,
    func_accepts_var_args,
    get_func_full_args,
    method_has_no_args,
)
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from .utils import get_view_name, strip_p_tags

# Exclude methods starting with these strings from documentation
MODEL_METHODS_EXCLUDE = ("_", "add_", "delete", "save", "set_")


class BaseAdminDocsView(TemplateView):
    """
    Base view for admindocs views.
    """

    @method_decorator(staff_member_required)
    def dispatch(self, request, *args, **kwargs):
        if not utils.docutils_is_available:
            # Display an error message for people without docutils
            self.template_name = "admin_doc/missing_docutils.html"
            return self.render_to_response(admin.site.each_context(request))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            **{
                **kwargs,
                **admin.site.each_context(self.request),
            }
        )


class BookmarkletsView(BaseAdminDocsView):
    template_name = "admin_doc/bookmarklets.html"


class TemplateTagIndexView(BaseAdminDocsView):
    template_name = "admin_doc/template_tag_index.html"

    def get_context_data(self, **kwargs):
        tags = []
        try:
            engine = Engine.get_default()
        except ImproperlyConfigured:
            # Non-trivial TEMPLATES settings aren't supported (#24125).
            pass
        else:
            app_libs = sorted(engine.template_libraries.items())
            builtin_libs = [("", lib) for lib in engine.template_builtins]
            for module_name, library in builtin_libs + app_libs:
                for tag_name, tag_func in library.tags.items():
                    title, body, metadata = utils.parse_docstring(tag_func.__doc__)
                    title = title and utils.parse_rst(
                        title, "tag", _("tag:") + tag_name
                    )
                    body = body and utils.parse_rst(body, "tag", _("tag:") + tag_name)
                    for key in metadata:
                        metadata[key] = utils.parse_rst(
                            metadata[key], "tag", _("tag:") + tag_name
                        )
                    tag_library = module_name.split(".")[-1]
                    tags.append(
                        {
                            "name": tag_name,
                            "title": title,
                            "body": body,
                            "meta": metadata,
                            "library": tag_library,
                        }
                    )
        return super().get_context_data(**{**kwargs, "tags": tags})


class TemplateFilterIndexView(BaseAdminDocsView):
    template_name = "admin_doc/template_filter_index.html"

    def get_context_data(self, **kwargs):
        filters = []
        try:
            engine = Engine.get_default()
        except ImproperlyConfigured:
            # Non-trivial TEMPLATES settings aren't supported (#24125).
            pass
        else:
            app_libs = sorted(engine.template_libraries.items())
            builtin_libs = [("", lib) for lib in engine.template_builtins]
            for module_name, library in builtin_libs + app_libs:
                for filter_name, filter_func in library.filters.items():
                    title, body, metadata = utils.parse_docstring(filter_func.__doc__)
                    title = title and utils.parse_rst(
                        title, "filter", _("filter:") + filter_name
                    )
                    body = body and utils.parse_rst(
                        body, "filter", _("filter:") + filter_name
                    )
                    for key in metadata:
                        metadata[key] = utils.parse_rst(
                            metadata[key], "filter", _("filter:") + filter_name
                        )
                    tag_library = module_name.split(".")[-1]
                    filters.append(
                        {
                            "name": filter_name,
                            "title": title,
                            "body": body,
                            "meta": metadata,
                            "library": tag_library,
                        }
                    )
        return super().get_context_data(**{**kwargs, "filters": filters})


class ViewIndexView(BaseAdminDocsView):
    template_name = "admin_doc/view_index.html"

    def get_context_data(self, **kwargs):
        views = []
        url_resolver = get_resolver(get_urlconf())
        try:
            view_functions = extract_views_from_urlpatterns(url_resolver.url_patterns)
        except ImproperlyConfigured:
            view_functions = []
        for func, regex, namespace, name in view_functions:
            views.append(
                {
                    "full_name": get_view_name(func),
                    "url": simplify_regex(regex),
                    "url_name": ":".join((namespace or []) + (name and [name] or [])),
                    "namespace": ":".join(namespace or []),
                    "name": name,
                }
            )
        return super().get_context_data(**{**kwargs, "views": views})


class ViewDetailView(BaseAdminDocsView):
    template_name = "admin_doc/view_detail.html"

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

    def get_context_data(self, **kwargs):
        view = self.kwargs["view"]
        view_func = self._get_view_func(view)
        if view_func is None:
            raise Http404
        title, body, metadata = utils.parse_docstring(view_func.__doc__)
        title = title and utils.parse_rst(title, "view", _("view:") + view)
        body = body and utils.parse_rst(body, "view", _("view:") + view)
        for key in metadata:
            metadata[key] = utils.parse_rst(metadata[key], "model", _("view:") + view)
        return super().get_context_data(
            **{
                **kwargs,
                "name": view,
                "summary": strip_p_tags(title),
                "body": body,
                "meta": metadata,
            }
        )


def user_has_model_view_permission(user, opts):
    """Based off ModelAdmin.has_view_permission."""
    codename_view = get_permission_codename("view", opts)
    codename_change = get_permission_codename("change", opts)
    return user.has_perm("%s.%s" % (opts.app_label, codename_view)) or user.has_perm(
        "%s.%s" % (opts.app_label, codename_change)
    )


class ModelIndexView(BaseAdminDocsView):
    template_name = "admin_doc/model_index.html"

    def get_context_data(self, **kwargs):
        m_list = [
            m._meta
            for m in apps.get_models()
            if user_has_model_view_permission(self.request.user, m._meta)
        ]
        return super().get_context_data(**{**kwargs, "models": m_list})


class ModelDetailView(BaseAdminDocsView):
    template_name = "admin_doc/model_detail.html"

    def get_context_data(self, **kwargs):
        model_name = self.kwargs["model_name"]
        # Get the model class.
        try:
            app_config = apps.get_app_config(self.kwargs["app_label"])
        except LookupError:
            raise Http404(_("App %(app_label)r not found") % self.kwargs)
        try:
            model = app_config.get_model(model_name)
        except LookupError:
            raise Http404(
                _("Model %(model_name)r not found in app %(app_label)r") % self.kwargs
            )

        opts = model._meta
        if not user_has_model_view_permission(self.request.user, opts):
            raise PermissionDenied

        title, body, metadata = utils.parse_docstring(model.__doc__)
        title = title and utils.parse_rst(title, "model", _("model:") + model_name)
        body = body and utils.parse_rst(body, "model", _("model:") + model_name)

        # Gather fields/field descriptions.
        fields = []
        for field in opts.fields:
            # ForeignKey is a special case since the field will actually be a
            # descriptor that returns the other object
            if isinstance(field, models.ForeignKey):
                data_type = field.remote_field.model.__name__
                app_label = field.remote_field.model._meta.app_label
                verbose = utils.parse_rst(
                    (
                        _("the related `%(app_label)s.%(data_type)s` object")
                        % {
                            "app_label": app_label,
                            "data_type": data_type,
                        }
                    ),
                    "model",
                    _("model:") + data_type,
                )
            else:
                data_type = get_readable_field_data_type(field)
                verbose = field.verbose_name
            fields.append(
                {
                    "name": field.name,
                    "data_type": data_type,
                    "verbose": verbose or "",
                    "help_text": field.help_text,
                }
            )

        # Gather many-to-many fields.
        for field in opts.many_to_many:
            data_type = field.remote_field.model.__name__
            app_label = field.remote_field.model._meta.app_label
            verbose = _("related `%(app_label)s.%(object_name)s` objects") % {
                "app_label": app_label,
                "object_name": data_type,
            }
            fields.append(
                {
                    "name": "%s.all" % field.name,
                    "data_type": "List",
                    "verbose": utils.parse_rst(
                        _("all %s") % verbose, "model", _("model:") + opts.model_name
                    ),
                }
            )
            fields.append(
                {
                    "name": "%s.count" % field.name,
                    "data_type": "Integer",
                    "verbose": utils.parse_rst(
                        _("number of %s") % verbose,
                        "model",
                        _("model:") + opts.model_name,
                    ),
                }
            )

        methods = []
        # Gather model methods.
        for func_name, func in model.__dict__.items():
            if inspect.isfunction(func) or isinstance(
                func, (cached_property, property)
            ):
                try:
                    for exclude in MODEL_METHODS_EXCLUDE:
                        if func_name.startswith(exclude):
                            raise StopIteration
                except StopIteration:
                    continue
                verbose = func.__doc__
                verbose = verbose and (
                    utils.parse_rst(
                        cleandoc(verbose), "model", _("model:") + opts.model_name
                    )
                )
                # Show properties, cached_properties, and methods without
                # arguments as fields. Otherwise, show as a 'method with
                # arguments'.
                if isinstance(func, (cached_property, property)):
                    fields.append(
                        {
                            "name": func_name,
                            "data_type": get_return_data_type(func_name),
                            "verbose": verbose or "",
                        }
                    )
                elif (
                    method_has_no_args(func)
                    and not func_accepts_kwargs(func)
                    and not func_accepts_var_args(func)
                ):
                    fields.append(
                        {
                            "name": func_name,
                            "data_type": get_return_data_type(func_name),
                            "verbose": verbose or "",
                        }
                    )
                else:
                    arguments = get_func_full_args(func)
                    # Join arguments with ', ' and in case of default value,
                    # join it with '='. Use repr() so that strings will be
                    # correctly displayed.
                    print_arguments = ", ".join(
                        [
                            "=".join([arg_el[0], *map(repr, arg_el[1:])])
                            for arg_el in arguments
                        ]
                    )
                    methods.append(
                        {
                            "name": func_name,
                            "arguments": print_arguments,
                            "verbose": verbose or "",
                        }
                    )

        # Gather related objects
        for rel in opts.related_objects:
            verbose = _("related `%(app_label)s.%(object_name)s` objects") % {
                "app_label": rel.related_model._meta.app_label,
                "object_name": rel.related_model._meta.object_name,
            }
            accessor = rel.accessor_name
            fields.append(
                {
                    "name": "%s.all" % accessor,
                    "data_type": "List",
                    "verbose": utils.parse_rst(
                        _("all %s") % verbose, "model", _("model:") + opts.model_name
                    ),
                }
            )
            fields.append(
                {
                    "name": "%s.count" % accessor,
                    "data_type": "Integer",
                    "verbose": utils.parse_rst(
                        _("number of %s") % verbose,
                        "model",
                        _("model:") + opts.model_name,
                    ),
                }
            )
        return super().get_context_data(
            **{
                **kwargs,
                "name": opts.label,
                "summary": strip_p_tags(title),
                "description": body,
                "fields": fields,
                "methods": methods,
            }
        )


class TemplateDetailView(BaseAdminDocsView):
    template_name = "admin_doc/template_detail.html"

    def get_context_data(self, **kwargs):
        template = self.kwargs["template"]
        templates = []
        try:
            default_engine = Engine.get_default()
        except ImproperlyConfigured:
            # Non-trivial TEMPLATES settings aren't supported (#24125).
            pass
        else:
            directories = list(default_engine.dirs)
            for loader in default_engine.template_loaders:
                if hasattr(loader, "get_dirs"):
                    for dir_ in loader.get_dirs():
                        if dir_ not in directories:
                            directories.append(dir_)
            for index, directory in enumerate(directories):
                template_file = Path(safe_join(directory, template))
                if template_file.exists():
                    template_contents = template_file.read_text()
                else:
                    template_contents = ""
                templates.append(
                    {
                        "file": template_file,
                        "exists": template_file.exists(),
                        "contents": template_contents,
                        "order": index,
                    }
                )
        return super().get_context_data(
            **{
                **kwargs,
                "name": template,
                "templates": templates,
            }
        )


####################
# Helper functions #
####################


def get_return_data_type(func_name):
    """Return a somewhat-helpful data type given a function name"""
    if func_name.startswith("get_"):
        if func_name.endswith("_list"):
            return "List"
        elif func_name.endswith("_count"):
            return "Integer"
    return ""


def get_readable_field_data_type(field):
    """
    Return the description for a given field type, if it exists. Fields'
    descriptions can contain format strings, which will be interpolated with
    the values of field.__dict__ before being output.
    """
    return field.description % field.__dict__


def extract_views_from_urlpatterns(urlpatterns, base="", namespace=None):
    """
    Return a list of views from a list of urlpatterns.

    Each object in the returned list is a 4-tuple:
    (view_func, regex, namespace, name)
    """
    views = []
    for p in urlpatterns:
        if hasattr(p, "url_patterns"):
            try:
                patterns = p.url_patterns
            except ImportError:
                continue
            views.extend(
                extract_views_from_urlpatterns(
                    patterns,
                    base + str(p.pattern),
                    (namespace or []) + (p.namespace and [p.namespace] or []),
                )
            )
        elif hasattr(p, "callback"):
            try:
                views.append((p.callback, base + str(p.pattern), namespace, p.name))
            except ViewDoesNotExist:
                continue
        else:
            raise TypeError(_("%s does not appear to be a urlpattern object") % p)
    return views


def simplify_regex(pattern):
    r"""
    Clean up urlpattern regexes into something more readable by humans. For
    example, turn "^(?P<sport_slug>\w+)/athletes/(?P<athlete_slug>\w+)/$"
    into "/<sport_slug>/athletes/<athlete_slug>/".
    """
    pattern = remove_non_capturing_groups(pattern)
    pattern = replace_named_groups(pattern)
    pattern = replace_unnamed_groups(pattern)
    pattern = replace_metacharacters(pattern)
    if not pattern.startswith("/"):
        pattern = "/" + pattern
    return pattern
