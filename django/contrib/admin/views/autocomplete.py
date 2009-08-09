import operator
from django.db import models
from django.db.models.query import QuerySet
from django.utils.encoding import smart_str
from django.http import HttpResponse, HttpResponseNotFound
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
 
def foreignkey_autocomplete(request, related_string_functions=None):
    """
    Searches in the fields of the given related model and returns the
    result as a simple string to be used by the jQuery Autocomplete plugin
    """
    if related_string_functions is None:
        related_string_functions = getattr(settings,
            'DJANGO_EXTENSIONS_FOREIGNKEY_AUTOCOMPLETE_STRING_FUNCTIONS', {})
    query = request.GET.get('q', None)
    app_label = request.GET.get('app_label', None)
    model_name = request.GET.get('model_name', None)
    search_fields = request.GET.get('search_fields', None)
    object_pk = request.GET.get('object_pk', None)
    try:
        to_string_function = related_string_functions[model_name]
    except KeyError:
        to_string_function = lambda x: unicode(x)
    if search_fields and app_label and model_name and (query or object_pk):
        def construct_search(field_name):
            # use different lookup methods depending on the notation
            if field_name.startswith('^'):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith('='):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith('@'):
                return "%s__search" % field_name[1:]
            else:
                return "%s__icontains" % field_name
        model = models.get_model(app_label, model_name)
        queryset = model._default_manager.all()
        data = ''
        if query:
            for bit in query.split():
                or_queries = [models.Q(**{construct_search(
                    smart_str(field_name)): smart_str(bit)})
                        for field_name in search_fields.split(',')]
                other_qs = QuerySet(model)
                other_qs.dup_select_related(queryset)
                other_qs = other_qs.filter(reduce(operator.or_, or_queries))
                queryset = queryset & other_qs
            data = ''.join([u'%s|%s\n' % (
                to_string_function(f), f.pk) for f in queryset])
        elif object_pk:
            try:
                obj = queryset.get(pk=object_pk)
            except:
                pass
            else:
                data = to_string_function(obj)
        return HttpResponse(data)
    return HttpResponseNotFound()
foreignkey_autocomplete = staff_member_required(foreignkey_autocomplete)