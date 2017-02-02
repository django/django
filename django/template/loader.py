from . import engines
from .exceptions import TemplateDoesNotExist


def get_template(template_name, using=None):
    """
    Loads and returns a template for the given name.

    Raises TemplateDoesNotExist if no such template exists.
    """
    chain = []
    engines = _engine_list(using)
    for engine in engines:
        try:
            return engine.get_template(template_name)
        except TemplateDoesNotExist as e:
            chain.append(e)

    raise TemplateDoesNotExist(template_name, chain=chain)


def select_template(template_name_list, using=None):
    """
    Loads and returns a template for one of the given names.

    Tries names in order and returns the first template found.

    Raises TemplateDoesNotExist if no such template exists.
    """
    if isinstance(template_name_list, str):
        raise TypeError(
            'select_template() takes an iterable of template names but got a '
            'string: %r. Use get_template() if you want to load a single '
            'template by name.' % template_name_list
        )

    chain = []
    engines = _engine_list(using)
    for template_name in template_name_list:
        for engine in engines:
            try:
                return engine.get_template(template_name)
            except TemplateDoesNotExist as e:
                chain.append(e)

    if template_name_list:
        raise TemplateDoesNotExist(', '.join(template_name_list), chain=chain)
    else:
        raise TemplateDoesNotExist("No template names provided")


def render_to_string(template_name, context=None, request=None, using=None):
    """
    Loads a template and renders it with a context. Returns a string.

    template_name may be a string or a list of strings.
    """
    if isinstance(template_name, (list, tuple)):
        template = select_template(template_name, using=using)
    else:
        template = get_template(template_name, using=using)
    return template.render(context, request)


def _engine_list(using=None):
    return engines.all() if using is None else [engines[using]]
