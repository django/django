from copy import copy


# Hard-coded processor for easier use of CSRF protection.
_builtin_context_processors = ('django.core.context_processors.csrf',)


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
    def __init__(self, dict_=None, autoescape=True, current_app=None,
            use_l10n=None, use_tz=None, engine=None):
        self.autoescape = autoescape
        self.current_app = current_app
        self.use_l10n = use_l10n
        self.use_tz = use_tz
        self.engine = engine
        self.render_context = RenderContext()
        super(Context, self).__init__(dict_)

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
    the processors defined in TEMPLATE_CONTEXT_PROCESSORS.
    Additional processors can be specified as a list of callables
    using the "processors" keyword argument.
    """
    def __init__(self, request, dict_=None, processors=None, current_app=None,
            use_l10n=None, use_tz=None, engine=None):
        Context.__init__(self, dict_, current_app=current_app,
                use_l10n=use_l10n, use_tz=use_tz, engine=engine)
        self._request = request
        self._processors = () if processors is None else tuple(processors)
        self._processors_index = len(self.dicts)
        self.update({})         # placeholder for context processors output
        self.engine = engine    # re-run the setter in case engine is not None

    @property
    def engine(self):
        return self._engine

    @engine.setter
    def engine(self, engine):
        self._engine = engine
        if hasattr(self, '_processors_index'):
            if engine is None:
                # Unset context processors.
                self.dicts[self._processors_index] = {}
            else:
                # Set context processors for this engine.
                updates = {}
                for processor in engine.template_context_processors + self._processors:
                    updates.update(processor(self._request))
                self.dicts[self._processors_index] = updates

    def new(self, values=None):
        new_context = super(RequestContext, self).new(values)
        # This is for backwards-compatibility: RequestContexts created via
        # Context.new don't include values from context processors.
        del new_context._processors_index
        return new_context
