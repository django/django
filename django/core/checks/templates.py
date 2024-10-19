from . import Tags, register


@register(Tags.templates)
def check_templates(app_configs, **kwargs):
    """Check all registered template engines."""
    from django.template import engines

    errors = []
    for engine in engines.all():
        errors.extend(engine.check())
    return errors
