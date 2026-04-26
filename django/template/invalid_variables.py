import logging

from . import Variable

logger = logging.getLogger("django.template")


def default_invalid_variable_handler(context, reason, variable=None, string_if_invalid=None):
    variable_name = None
    if variable and isinstance(variable, Variable):
        variable_name = variable.var

    template_name = getattr(context, "template_name", None) or "unknown"
    logger.debug(
        "Exception while resolving variable '%s' in template '%s'.",
        variable_name,
        template_name,
        exc_info=True,
    )

    if string_if_invalid is None:
        try:
            string_if_invalid = context.template.engine.string_if_invalid
        except AttributeError:
            string_if_invalid = ""
    
    if "%s" in string_if_invalid and variable_name is not None:
        return string_if_invalid % variable_name
    else:
        return string_if_invalid


class BaseInvalidVariableType:

    def __init__(self, variable, context, reason, **kwargs):
        self.variable = variable
        self.context = context
        self.reason = reason
        self.run_side_effects()

    @property
    def template_name(self):
        return getattr(self.context, "template_name", None) or "unknown"

    @property
    def variable_name(self):
        if isinstance(self.variable, Variable):
            return self.variable.var
        if callable(self.variable):
            if hasattr(self.variable, "__name__"):
                return self.variable.__name__
            if hasattr(self.variable, "__qualname__"):
                return self.variable.__qualname__
            if hasattr(self.variable, "__class__"):
                return self.variable.__class__.__name__
        return "unknown"

    def should_apply_filters(self):
        return True

    def render(self):
        raise Exception(f"Invalid variable '{self.variable_name}' in template '{self.template_name}'")

    def run_side_effects(self):
        pass

    def __str__(self):
        return self.render()

    def __bool__(self):
        return not self.should_apply_filters()