import warnings
from contextlib import contextmanager
from copy import copy

from django.utils.deprecation import RemovedInDjango20Warning

# Hard-coded processor for easier use of CSRF protection.
_builtin_context_processors = ('django.template.context_processors.csrf',)

_current_app_undefined = object()


class ContextPopException(Exception):
    "pop() has been called more times than push()"
    pass


class ContextDict(dict):
    def __init__(self, context, *args, **kwargs):
        super(ContextDict, self).__init__(*args, **kwargs)

        context.dicts.append(self)
        self.context = context

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        self.context.pop()


class BaseContext(object):
    def __init__(self, dict_=None):
        self._reset_dicts(dict_)

    def _reset_dicts(self, value=None):
        builtins = {'True': True, 'False': False, 'None': None}
        self.dicts = [builtins]
        if value is not None:
            self.dicts.append(value)

    def __copy__(self):
        duplicate = copy(super(BaseContext, self))
        duplicate.dicts = self.dicts[:]
        return duplicate

    def __repr__(self):
        return repr(self.dicts)

    def __iter__(self):
        for d in reversed(self.dicts):
            yield d

    def push(self, *args, **kwargs):
        return ContextDict(self, *args, **kwargs)

    def pop(self):
        if len(self.dicts) == 1:
            raise ContextPopException
        return self.dicts.pop()

    def __setitem__(self, key, value):
        "Set a variable in the current context"
        self.dicts[-1][key] = value

    def __getitem__(self, key):
        "Get a variable's value, starting at the current context and going upward"
        for d in reversed(self.dicts):
            if key in d:
                return d[key]
        raise KeyError(key)

    def __delitem__(self, key):
        "Delete a variable from the current context"
        del self.dicts[-1][key]

    def has_key(self, key):
        for d in self.dicts:
            if key in d:
                return True
        return False

    def __contains__(self, key):
        return self.has_key(key)

    def get(self, key, otherwise=None):
        for d in reversed(self.dicts):
            if key in d:
                return d[key]
        return otherwise

    def new(self, values=None):
        """
        Returns a new context with the same properties, but with only the
        values given in 'values' stored.
        """
        new_context = copy(self)
        new_context._reset_dicts(values)
        return new_context

    def flatten(self):
        """
        Returns self.dicts as one dictionary
        """
        flat = {}
        for d in self.dicts:
            flat.update(d)
        return flat

    def __eq__(self, other):
        """
        Compares two contexts by comparing theirs 'dicts' attributes.
        """
        if isinstance(other, BaseContext):
            # because dictionaries can be put in different order
            # we have to flatten them like in templates
            return self.flatten() == other.flatten()

        # if it's not comparable return false
        return False


class Context(BaseContext):
    "A stack container for variable context"
    def __init__(self, dict_=None, autoescape=True,
            current_app=_current_app_undefined,
            use_l10n=None, use_tz=None):
        if current_app is not _current_app_undefined:
            warnings.warn(
                "The current_app argument of Context is deprecated. Use "
                "RequestContext and set the current_app attribute of its "
                "request instead.", RemovedInDjango20Warning, stacklevel=2)
        self.autoescape = autoescape
        self._current_app = current_app
        self.use_l10n = use_l10n
        self.use_tz = use_tz
        self.render_context = RenderContext()
        # Set to the original template -- as opposed to extended or included
        # templates -- during rendering, see bind_template.
        self.template = None
        super(Context, self).__init__(dict_)

    @property
    def current_app(self):
        return None if self._current_app is _current_app_undefined else self._current_app

    @contextmanager
    def bind_template(self, template):
        if self.template is not None:
            raise RuntimeError("Context is already bound to a template")
        self.template = template
        try:
            yield
        finally:
            self.template = None

    def __copy__(self):
        duplicate = super(Context, self).__copy__()
        duplicate.render_context = copy(self.render_context)
        return duplicate

    def update(self, other_dict):
        "Pushes other_dict to the stack of dictionaries in the Context"
        if not hasattr(other_dict, '__getitem__'):
            raise TypeError('other_dict must be a mapping (dictionary-like) object.')
        self.dicts.append(other_dict)
        return other_dict


class RenderContext(BaseContext):
    """
    A stack container for storing Template state.

    RenderContext simplifies the implementation of template Nodes by providing a
    safe place to store state between invocations of a node's `render` method.

    The RenderContext also provides scoping rules that are more sensible for
    'template local' variables. The render context stack is pushed before each
    template is rendered, creating a fresh scope with nothing in it. Name
    resolution fails if a variable is not found at the top of the RequestContext
    stack. Thus, variables are local to a specific template and don't affect the
    rendering of other templates as they would if they were stored in the normal
    template context.
    """
    def __iter__(self):
        for d in self.dicts[-1]:
            yield d

    def has_key(self, key):
        return key in self.dicts[-1]

    def get(self, key, otherwise=None):
        return self.dicts[-1].get(key, otherwise)

    def __getitem__(self, key):
        return self.dicts[-1][key]


class RequestContext(Context):
    """
    This subclass of template.Context automatically populates itself using
    the processors defined in the engine's configuration.
    Additional processors can be specified as a list of callables
    using the "processors" keyword argument.
    """
    def __init__(self, request, dict_=None, processors=None,
            current_app=_current_app_undefined,
            use_l10n=None, use_tz=None):
        # current_app isn't passed here to avoid triggering the deprecation
        # warning in Context.__init__.
        super(RequestContext, self).__init__(
            dict_, use_l10n=use_l10n, use_tz=use_tz)
        if current_app is not _current_app_undefined:
            warnings.warn(
                "The current_app argument of RequestContext is deprecated. "
                "Set the current_app attribute of its request instead.",
                RemovedInDjango20Warning, stacklevel=2)
        self._current_app = current_app
        self.request = request
        self._processors = () if processors is None else tuple(processors)
        self._processors_index = len(self.dicts)
        self.update({})         # placeholder for context processors output

    @contextmanager
    def bind_template(self, template):
        if self.template is not None:
            raise RuntimeError("Context is already bound to a template")

        self.template = template
        # Set context processors according to the template engine's settings.
        processors = (template.engine.template_context_processors +
                      self._processors)
        updates = {}
        for processor in processors:
            updates.update(processor(self.request))
        self.dicts[self._processors_index] = updates

        try:
            yield
        finally:
            self.template = None
            # Unset context processors.
            self.dicts[self._processors_index] = {}

    def new(self, values=None):
        new_context = super(RequestContext, self).new(values)
        # This is for backwards-compatibility: RequestContexts created via
        # Context.new don't include values from context processors.
        if hasattr(new_context, '_processors_index'):
            del new_context._processors_index
        return new_context


def make_context(context, request=None):
    """
    Create a suitable Context from a plain dict and optionally an HttpRequest.
    """
    if request is None:
        context = Context(context)
    else:
        # The following pattern is required to ensure values from
        # context override those from template context processors.
        original_context = context
        context = RequestContext(request)
        if original_context:
            context.push(original_context)
    return context
