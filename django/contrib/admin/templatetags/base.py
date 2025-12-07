from inspect import getfullargspec

from django.template.exceptions import TemplateSyntaxError
from django.template.library import InclusionNode, parse_bits
from django.utils.inspect import lazy_annotations


class InclusionAdminNode(InclusionNode):
    """
    Template tag that allows its template to be overridden per model, per app,
    or globally.
    """

    def __init__(self, name, parser, token, func, template_name, takes_context=True):
        self.template_name = template_name
        with lazy_annotations():
            params, varargs, varkw, defaults, kwonly, kwonly_defaults, _ = (
                getfullargspec(func)
            )
        if takes_context:
            if params and params[0] == "context":
                del params[0]
            else:
                function_name = func.__name__
                raise TemplateSyntaxError(
                    f"{name!r} sets takes_context=True so {function_name!r} "
                    "must have a first argument of 'context'"
                )
        bits = token.split_contents()
        args, kwargs = parse_bits(
            parser,
            bits[1:],
            params,
            varargs,
            varkw,
            defaults,
            kwonly,
            kwonly_defaults,
            bits[0],
        )
        super().__init__(func, takes_context, args, kwargs, filename=None)

    def render(self, context):
        opts = context["opts"]
        app_label = opts.app_label.lower()
        object_name = opts.model_name
        # Load template for this render call. (Setting self.filename isn't
        # thread-safe.)
        context.render_context[self] = context.template.engine.select_template(
            [
                "admin/%s/%s/%s" % (app_label, object_name, self.template_name),
                "admin/%s/%s" % (app_label, self.template_name),
                "admin/%s" % self.template_name,
            ]
        )
        return super().render(context)
