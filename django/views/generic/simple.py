from django.core import template_loader
from django.core.extensions import DjangoContext
from django.utils.httpwrappers import HttpResponse

def direct_to_template(request, template, **kwargs):
    """Render a given template with any extra parameters in the context."""
    t = template_loader.get_template(template)
    c = DjangoContext(request, {'params' : kwargs})
    return HttpResponse(t.render(c))