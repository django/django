import functools
import inspect
import itertools
import re
import sys
import types
import warnings
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse, HttpResponseNotFound
from django.template import Context, Engine, TemplateDoesNotExist
from django.template.defaultfilters import pprint
from django.urls import resolve
from django.utils import timezone
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_str
from django.utils.module_loading import import_string
from django.utils.regex_helper import _lazy_re_compile
from django.utils.version import get_docs_version
from django.views.decorators.debug import coroutine_functions_to_sensitive_variables

# Minimal Django templates engine to render the error templates
# regardless of the project's TEMPLATES setting. Templates are
# read directly from the filesystem so that the error handler
# works even if the template loader is broken.
DEBUG_ENGINE = Engine(
    debug=True,
    libraries={"i18n": "django.templatetags.i18n"},
)


def builtin_template_path(name):
    """
    Return a path to a builtin template.

    Avoid calling this function at the module level or in a class-definition
    because __file__ may not exist, e.g. in frozen environments.
    """
    return Path(__file__).parent / "templates" / name


class ExceptionCycleWarning(UserWarning):
    pass


class CallableSettingWrapper:
    """
    Object to wrap callable appearing in settings.
    * Not to call in the debug page (#21345).
    * Not to break the debug page if the callable forbidding to set attributes
      (#23070).
    """

    def __init__(self, callable_setting):
        self._wrapped = callable_setting

    def __repr__(self):
        return repr(self._wrapped)


def technical_500_response(request, exc_type, exc_value, tb, status_code=500):
    """
    Create a technical server error response. The last three arguments are
    the values returned from sys.exc_info() and friends.
    """
    reporter = get_exception_reporter_class(request)(request, exc_type, exc_value, tb)
    if request.accepts("text/html"):
        html = reporter.get_traceback_html()
        return HttpResponse(html, status=status_code)
    else:
        text = reporter.get_traceback_text()
        return HttpResponse(
            text, status=status_code, content_type="text/plain; charset=utf-8"
        )


@functools.lru_cache
def get_default_exception_reporter_filter():
    # Instantiate the default filter for the first time and cache it.
    return import_string(settings.DEFAULT_EXCEPTION_REPORTER_FILTER)()


def get_exception_reporter_filter(request):
    default_filter = get_default_exception_reporter_filter()
    return getattr(request, "exception_reporter_filter", default_filter)


def get_exception_reporter_class(request):
    default_exception_reporter_class = import_string(
        settings.DEFAULT_EXCEPTION_REPORTER
    )
    return getattr(
        request, "exception_reporter_class", default_exception_reporter_class
    )


def get_caller(request):
    resolver_match = request.resolver_match
    if resolver_match is None:
        try:
            resolver_match = resolve(request.path)
        except Http404:
            pass
    return "" if resolver_match is None else resolver_match._func_path


class SafeExceptionReporterFilter:
    """
    Use annotations made by the sensitive_post_parameters and
    sensitive_variables decorators to filter out sensitive information.
    """

    cleansed_substitute = "********************"
    hidden_settings = _lazy_re_compile(
        "API|AUTH|TOKEN|KEY|SECRET|PASS|SIGNATURE|HTTP_COOKIE", flags=re.I
    )

    def cleanse_setting(self, key, value):
        """
        Cleanse an individual setting key/value of sensitive content. If the
        value is a dictionary, recursively cleanse the keys in that dictionary.
        """
        if key == settings.SESSION_COOKIE_NAME:
            is_sensitive = True
        else:
            try:
                is_sensitive = self.hidden_settings.search(key)
            except TypeError:
                is_sensitive = False

        if is_sensitive:
            cleansed = self.cleansed_substitute
        elif isinstance(value, dict):
            cleansed = {k: self.cleanse_setting(k, v) for k, v in value.items()}
        elif isinstance(value, list):
            cleansed = [self.cleanse_setting("", v) for v in value]
        elif isinstance(value, tuple):
            cleansed = tuple([self.cleanse_setting("", v) for v in value])
        else:
            cleansed = value

        if callable(cleansed):
            cleansed = CallableSettingWrapper(cleansed)

        return cleansed

    def get_safe_settings(self):
        """
        Return a dictionary of the settings module with values of sensitive
        settings replaced with stars (*********).
        """
        settings_dict = {}
        for k in dir(settings):
            if k.isupper():
                settings_dict[k] = self.cleanse_setting(k, getattr(settings, k))
        return settings_dict

    def get_safe_request_meta(self, request):
        """
        Return a dictionary of request.META with sensitive values redacted.
        """
        if not hasattr(request, "META"):
            return {}
        return {k: self.cleanse_setting(k, v) for k, v in request.META.items()}

    def get_safe_cookies(self, request):
        """
        Return a dictionary of request.COOKIES with sensitive values redacted.
        """
        if not hasattr(request, "COOKIES"):
            return {}
        return {k: self.cleanse_setting(k, v) for k, v in request.COOKIES.items()}

    def is_active(self, request):
        """
        This filter is to add safety in production environments (i.e. DEBUG
        is False). If DEBUG is True then your site is not safe anyway.
        This hook is provided as a convenience to easily activate or
        deactivate the filter on a per request basis.
        """
        return settings.DEBUG is False

    def get_cleansed_multivaluedict(self, request, multivaluedict):
        """
        Replace the keys in a MultiValueDict marked as sensitive with stars.
        This mitigates leaking sensitive POST parameters if something like
        request.POST['nonexistent_key'] throws an exception (#21098).
        """
        sensitive_post_parameters = getattr(request, "sensitive_post_parameters", [])
        if self.is_active(request) and sensitive_post_parameters:
            multivaluedict = multivaluedict.copy()
            for param in sensitive_post_parameters:
                if param in multivaluedict:
                    multivaluedict[param] = self.cleansed_substitute
        return multivaluedict

    def get_post_parameters(self, request):
        """
        Replace the values of POST parameters marked as sensitive with
        stars (*********).
        """
        if request is None:
            return {}
        else:
            sensitive_post_parameters = getattr(
                request, "sensitive_post_parameters", []
            )
            if self.is_active(request) and sensitive_post_parameters:
                cleansed = request.POST.copy()
                if sensitive_post_parameters == "__ALL__":
                    # Cleanse all parameters.
                    for k in cleansed:
                        cleansed[k] = self.cleansed_substitute
                    return cleansed
                else:
                    # Cleanse only the specified parameters.
                    for param in sensitive_post_parameters:
                        if param in cleansed:
                            cleansed[param] = self.cleansed_substitute
                    return cleansed
            else:
                return request.POST

    def cleanse_special_types(self, request, value):
        try:
            # If value is lazy or a complex object of another kind, this check
            # might raise an exception. isinstance checks that lazy
            # MultiValueDicts will have a return value.
            is_multivalue_dict = isinstance(value, MultiValueDict)
        except Exception as e:
            return "{!r} while evaluating {!r}".format(e, value)

        if is_multivalue_dict:
            # Cleanse MultiValueDicts (request.POST is the one we usually care about)
            value = self.get_cleansed_multivaluedict(request, value)
        return value

    def get_traceback_frame_variables(self, request, tb_frame):
        """
        Replace the values of variables marked as sensitive with
        stars (*********).
        """
        sensitive_variables = None

        # Coroutines don't have a proper `f_back` so they need to be inspected
        # separately. Handle this by stashing the registered sensitive
        # variables in a global dict indexed by `hash(file_path:line_number)`.
        if (
            tb_frame.f_code.co_flags & inspect.CO_COROUTINE != 0
            and tb_frame.f_code.co_name != "sensitive_variables_wrapper"
        ):
            key = hash(
                f"{tb_frame.f_code.co_filename}:{tb_frame.f_code.co_firstlineno}"
            )
            sensitive_variables = coroutine_functions_to_sensitive_variables.get(
                key, None
            )

        if sensitive_variables is None:
            # Loop through the frame's callers to see if the
            # sensitive_variables decorator was used.
            current_frame = tb_frame
            while current_frame is not None:
                if (
                    current_frame.f_code.co_name == "sensitive_variables_wrapper"
                    and "sensitive_variables_wrapper" in current_frame.f_locals
                ):
                    # The sensitive_variables decorator was used, so take note
                    # of the sensitive variables' names.
                    wrapper = current_frame.f_locals["sensitive_variables_wrapper"]
                    sensitive_variables = getattr(wrapper, "sensitive_variables", None)
                    break
                current_frame = current_frame.f_back

        cleansed = {}
        if self.is_active(request) and sensitive_variables:
            if sensitive_variables == "__ALL__":
                # Cleanse all variables
                for name in tb_frame.f_locals:
                    cleansed[name] = self.cleansed_substitute
            else:
                # Cleanse specified variables
                for name, value in tb_frame.f_locals.items():
                    if name in sensitive_variables:
                        value = self.cleansed_substitute
                    else:
                        value = self.cleanse_special_types(request, value)
                    cleansed[name] = value
        else:
            # Potentially cleanse the request and any MultiValueDicts if they
            # are one of the frame variables.
            for name, value in tb_frame.f_locals.items():
                cleansed[name] = self.cleanse_special_types(request, value)

        if (
            tb_frame.f_code.co_name == "sensitive_variables_wrapper"
            and "sensitive_variables_wrapper" in tb_frame.f_locals
        ):
            # For good measure, obfuscate the decorated function's arguments in
            # the sensitive_variables decorator's frame, in case the variables
            # associated with those arguments were meant to be obfuscated from
            # the decorated function's frame.
            cleansed["func_args"] = self.cleansed_substitute
            cleansed["func_kwargs"] = self.cleansed_substitute

        return cleansed.items()


class ExceptionReporter:
    """Organize and coordinate reporting on exceptions."""

    @property
    def html_template_path(self):
        return builtin_template_path("technical_500.html")

    @property
    def text_template_path(self):
        return builtin_template_path("technical_500.txt")

    def __init__(self, request, exc_type, exc_value, tb, is_email=False):
        self.request = request
        self.filter = get_exception_reporter_filter(self.request)
        self.exc_type = exc_type
        self.exc_value = exc_value
        self.tb = tb
        self.is_email = is_email

        self.template_info = getattr(self.exc_value, "template_debug", None)
        self.template_does_not_exist = False
        self.postmortem = None

    def _get_raw_insecure_uri(self):
        """
        Return an absolute URI from variables available in this request. Skip
        allowed hosts protection, so may return insecure URI.
        """
        return "{scheme}://{host}{path}".format(
            scheme=self.request.scheme,
            host=self.request._get_raw_host(),
            path=self.request.get_full_path(),
        )

    def get_traceback_data(self):
        """Return a dictionary containing traceback information."""
        if self.exc_type and issubclass(self.exc_type, TemplateDoesNotExist):
            self.template_does_not_exist = True
            self.postmortem = self.exc_value.chain or [self.exc_value]

        frames = self.get_traceback_frames()
        for i, frame in enumerate(frames):
            if "vars" in frame:
                frame_vars = []
                for k, v in frame["vars"]:
                    v = pprint(v)
                    # Trim large blobs of data
                    if len(v) > 4096:
                        v = "%s… <trimmed %d bytes string>" % (v[0:4096], len(v))
                    frame_vars.append((k, v))
                frame["vars"] = frame_vars
            frames[i] = frame

        unicode_hint = ""
        if self.exc_type and issubclass(self.exc_type, UnicodeError):
            start = getattr(self.exc_value, "start", None)
            end = getattr(self.exc_value, "end", None)
            if start is not None and end is not None:
                unicode_str = self.exc_value.args[1]
                unicode_hint = force_str(
                    unicode_str[max(start - 5, 0) : min(end + 5, len(unicode_str))],
                    "ascii",
                    errors="replace",
                )
        from django import get_version

        if self.request is None:
            user_str = None
        else:
            try:
                user_str = str(self.request.user)
            except Exception:
                # request.user may raise OperationalError if the database is
                # unavailable, for example.
                user_str = "[unable to retrieve the current user]"

        c = {
            "is_email": self.is_email,
            "unicode_hint": unicode_hint,
            "frames": frames,
            "request": self.request,
            "request_meta": self.filter.get_safe_request_meta(self.request),
            "request_COOKIES_items": self.filter.get_safe_cookies(self.request).items(),
            "user_str": user_str,
            "filtered_POST_items": list(
                self.filter.get_post_parameters(self.request).items()
            ),
            "settings": self.filter.get_safe_settings(),
            "sys_executable": sys.executable,
            "sys_version_info": "%d.%d.%d" % sys.version_info[0:3],
            "server_time": timezone.now(),
            "django_version_info": get_version(),
            "sys_path": sys.path,
            "template_info": self.template_info,
            "template_does_not_exist": self.template_does_not_exist,
            "postmortem": self.postmortem,
        }
        if self.request is not None:
            c["request_GET_items"] = self.request.GET.items()
            c["request_FILES_items"] = self.request.FILES.items()
            c["request_insecure_uri"] = self._get_raw_insecure_uri()
            c["raising_view_name"] = get_caller(self.request)

        # Check whether exception info is available
        if self.exc_type:
            c["exception_type"] = self.exc_type.__name__
        if self.exc_value:
            c["exception_value"] = str(self.exc_value)
            if exc_notes := getattr(self.exc_value, "__notes__", None):
                c["exception_notes"] = "\n" + "\n".join(exc_notes)
        if frames:
            c["lastframe"] = frames[-1]
        return c

    def get_traceback_html(self):
        """Return HTML version of debug 500 HTTP error page."""
        with self.html_template_path.open(encoding="utf-8") as fh:
            t = DEBUG_ENGINE.from_string(fh.read())
        c = Context(self.get_traceback_data(), use_l10n=False)
        return t.render(c)

    def get_traceback_text(self):
        """Return plain text version of debug 500 HTTP error page."""
        with self.text_template_path.open(encoding="utf-8") as fh:
            t = DEBUG_ENGINE.from_string(fh.read())
        c = Context(self.get_traceback_data(), autoescape=False, use_l10n=False)
        return t.render(c)

    def _get_source(self, filename, loader, module_name):
        source = None
        if hasattr(loader, "get_source"):
            try:
                source = loader.get_source(module_name)
            except ImportError:
                pass
            if source is not None:
                source = source.splitlines()
        if source is None:
            try:
                with open(filename, "rb") as fp:
                    source = fp.read().splitlines()
            except OSError:
                pass
        return source

    def _get_lines_from_file(
        self, filename, lineno, context_lines, loader=None, module_name=None
    ):
        """
        Return context_lines before and after lineno from file.
        Return (pre_context_lineno, pre_context, context_line, post_context).
        """
        source = self._get_source(filename, loader, module_name)
        if source is None:
            return None, [], None, []

        # If we just read the source from a file, or if the loader did not
        # apply tokenize.detect_encoding to decode the source into a
        # string, then we should do that ourselves.
        if isinstance(source[0], bytes):
            encoding = "ascii"
            for line in source[:2]:
                # File coding may be specified. Match pattern from PEP-263
                # (https://www.python.org/dev/peps/pep-0263/)
                match = re.search(rb"coding[:=]\s*([-\w.]+)", line)
                if match:
                    encoding = match[1].decode("ascii")
                    break
            source = [str(sline, encoding, "replace") for sline in source]

        lower_bound = max(0, lineno - context_lines)
        upper_bound = lineno + context_lines

        try:
            pre_context = source[lower_bound:lineno]
            context_line = source[lineno]
            post_context = source[lineno + 1 : upper_bound]
        except IndexError:
            return None, [], None, []
        return lower_bound, pre_context, context_line, post_context

    def _get_explicit_or_implicit_cause(self, exc_value):
        explicit = getattr(exc_value, "__cause__", None)
        suppress_context = getattr(exc_value, "__suppress_context__", None)
        implicit = getattr(exc_value, "__context__", None)
        return explicit or (None if suppress_context else implicit)

    def get_traceback_frames(self):
        # Get the exception and all its causes
        exceptions = []
        exc_value = self.exc_value
        while exc_value:
            exceptions.append(exc_value)
            exc_value = self._get_explicit_or_implicit_cause(exc_value)
            if exc_value in exceptions:
                warnings.warn(
                    "Cycle in the exception chain detected: exception '%s' "
                    "encountered again." % exc_value,
                    ExceptionCycleWarning,
                )
                # Avoid infinite loop if there's a cyclic reference (#29393).
                break

        frames = []
        # No exceptions were supplied to ExceptionReporter
        if not exceptions:
            return frames

        # In case there's just one exception, take the traceback from self.tb
        exc_value = exceptions.pop()
        tb = self.tb if not exceptions else exc_value.__traceback__
        while True:
            frames.extend(self.get_exception_traceback_frames(exc_value, tb))
            try:
                exc_value = exceptions.pop()
            except IndexError:
                break
            tb = exc_value.__traceback__
        return frames

    def get_exception_traceback_frames(self, exc_value, tb):
        exc_cause = self._get_explicit_or_implicit_cause(exc_value)
        exc_cause_explicit = getattr(exc_value, "__cause__", True)
        if tb is None:
            yield {
                "exc_cause": exc_cause,
                "exc_cause_explicit": exc_cause_explicit,
                "tb": None,
                "type": "user",
            }
        while tb is not None:
            # Support for __traceback_hide__ which is used by a few libraries
            # to hide internal frames.
            if tb.tb_frame.f_locals.get("__traceback_hide__"):
                tb = tb.tb_next
                continue
            filename = tb.tb_frame.f_code.co_filename
            function = tb.tb_frame.f_code.co_name
            lineno = tb.tb_lineno - 1
            loader = tb.tb_frame.f_globals.get("__loader__")
            module_name = tb.tb_frame.f_globals.get("__name__") or ""
            (
                pre_context_lineno,
                pre_context,
                context_line,
                post_context,
            ) = self._get_lines_from_file(
                filename,
                lineno,
                7,
                loader,
                module_name,
            )
            if pre_context_lineno is None:
                pre_context_lineno = lineno
                pre_context = []
                context_line = "<source code not available>"
                post_context = []

            colno = tb_area_colno = ""
            _, _, start_column, end_column = next(
                itertools.islice(
                    tb.tb_frame.f_code.co_positions(), tb.tb_lasti // 2, None
                )
            )
            if start_column and end_column:
                underline = "^" * (end_column - start_column)
                spaces = " " * (start_column + len(str(lineno + 1)) + 2)
                colno = f"\n{spaces}{underline}"
                tb_area_spaces = " " * (
                    4 + start_column - (len(context_line) - len(context_line.lstrip()))
                )
                tb_area_colno = f"\n{tb_area_spaces}{underline}"
            yield {
                "exc_cause": exc_cause,
                "exc_cause_explicit": exc_cause_explicit,
                "tb": tb,
                "type": "django" if module_name.startswith("django.") else "user",
                "filename": filename,
                "function": function,
                "lineno": lineno + 1,
                "vars": self.filter.get_traceback_frame_variables(
                    self.request, tb.tb_frame
                ),
                "id": id(tb),
                "pre_context": pre_context,
                "context_line": context_line,
                "post_context": post_context,
                "pre_context_lineno": pre_context_lineno + 1,
                "colno": colno,
                "tb_area_colno": tb_area_colno,
            }
            tb = tb.tb_next


def technical_404_response(request, exception):
    """Create a technical 404 error response. `exception` is the Http404."""
    try:
        error_url = exception.args[0]["path"]
    except (IndexError, TypeError, KeyError):
        error_url = request.path_info[1:]  # Trim leading slash

    try:
        tried = exception.args[0]["tried"]
    except (IndexError, TypeError, KeyError):
        resolved = True
        tried = request.resolver_match.tried if request.resolver_match else None
    else:
        resolved = False
        if not tried or (  # empty URLconf
            request.path_info == "/"
            and len(tried) == 1
            and len(tried[0]) == 1  # default URLconf
            and getattr(tried[0][0], "app_name", "")
            == getattr(tried[0][0], "namespace", "")
            == "admin"
        ):
            return default_urlconf(request)

    urlconf = getattr(request, "urlconf", settings.ROOT_URLCONF)
    if isinstance(urlconf, types.ModuleType):
        urlconf = urlconf.__name__

    with builtin_template_path("technical_404.html").open(encoding="utf-8") as fh:
        t = DEBUG_ENGINE.from_string(fh.read())
    reporter_filter = get_default_exception_reporter_filter()
    c = Context(
        {
            "urlconf": urlconf,
            "root_urlconf": settings.ROOT_URLCONF,
            "request_path": error_url,
            "urlpatterns": tried,
            "resolved": resolved,
            "reason": str(exception),
            "request": request,
            "settings": reporter_filter.get_safe_settings(),
            "raising_view_name": get_caller(request),
        }
    )
    return HttpResponseNotFound(t.render(c))


def default_urlconf(request):
    """Create an empty URLconf 404 error response."""
    with builtin_template_path("default_urlconf.html").open(encoding="utf-8") as fh:
        t = DEBUG_ENGINE.from_string(fh.read())
    c = Context(
        {
            "version": get_docs_version(),
        }
    )

    return HttpResponse(t.render(c))
