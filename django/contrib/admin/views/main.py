# Generic admin views.
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.core import formfields, template
from django.core.template import loader
from django.db import models
from django.core.exceptions import Http404, ImproperlyConfigured, ObjectDoesNotExist, PermissionDenied
from django.core.extensions import DjangoContext as Context
from django.core.extensions import get_object_or_404, render_to_response
from django.utils import dateformat
from django.utils.html import escape, strip_tags
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.text import capfirst, get_text_list
import operator
from itertools import izip

ADMIN_PREFIX = "/admin/"

#def _get_mod_opts(app_label, module_name):
#    "Helper function that returns a tuple of (module, opts), raising Http404 if necessary."
#    try:
#        mod = models.get_app(app_label)
#    except ImportError:
#        raise Http404 # Invalid app or module name. Maybe it's not in INSTALLED_APPS.
#    opts = mod.Klass._meta
#    if not opts.admin:
#        raise Http404 # This object is valid but has no admin interface.
#    return mod, opts

def matches_app(mod, comps):
    modcomps = mod.__name__.split('.')[:-1] #HACK: leave off 'models'
    for c, mc in izip(comps, modcomps):
        if c != mc:
            return ([], False)
    return (comps[len(modcomps):], True)

def find_model(mod, remaining):
   # print "finding ", mod, remaining
    if len(remaining) == 0:
       # print "no comps left"
        raise Http404
    if len(remaining) == 1:
        if hasattr(mod, '_MODELS'):
            name = remaining[0]
            for model in mod._MODELS:
                if model.__name__.lower() == name:
                    return model
            raise Http404
        else:
            raise Http404
    else:
        child = getattr(mod, remaining[0], None)
       # print mod, remaining[0], child
        if child:
            return find_model(child, remaining[1:])
        else:
            raise Http404

def get_app_label(mod):
    #HACK
    return mod.__name__.split('.')[-2]

def get_model_and_app(path):
    comps = path.split('/')
    comps = comps[:-1] # remove '' after final /
    for mod in models.get_installed_models():
        remaining, matched = matches_app(mod, comps)
        if matched and len(remaining) > 0:
           # print "matched ", mod
           # print "left", remaining
            return (find_model(mod, remaining), get_app_label(mod))

    raise Http404 # Couldn't find app

_model_urls = {}

def url_for_model(model):
    try:
        return _model_urls[model]
    except KeyError:
        comps = model.__module__.split('.')
        for mod in models.get_installed_models():
            remaining, matched =  matches_app(mod, comps)
            if matched and len(remaining) > 0:
                comps = comps[:-len(remaining)] + remaining[1:]
                url = "%s%s/%s/" % (ADMIN_PREFIX, '/'.join(comps) , model.__name__.lower())
                _model_urls[model] = url
                return url
        raise ImproperlyConfigured, '%s is not a model in an installed app' % model.__name__

def index(request):
    return render_to_response('admin/index', {'title': _('Site administration')}, context_instance=Context(request))
index = staff_member_required(index)

def history(request, app_label, module_name, object_id):
    mod, opts = _get_mod_opts(app_label, module_name)
    action_list = LogEntry.objects.get_list(object_id__exact=object_id, content_type__id__exact=opts.get_content_type_id(),
        order_by=("action_time",), select_related=True)
    # If no history was found, see whether this object even exists.
    obj = get_object_or_404(mod, pk=object_id)
    return render_to_response('admin/object_history', {
        'title': _('Change history: %s') % obj,
        'action_list': action_list,
        'module_name': capfirst(opts.verbose_name_plural),
        'object': obj,
    }, context_instance=Context(request))
history = staff_member_required(history)
