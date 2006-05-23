from django.template import loader, RequestContext
from django.http import Http404, HttpResponse
from django.core.xheaders import populate_xheaders
from django.core.paginator import ObjectPaginator, InvalidPage
from django.core.exceptions import ObjectDoesNotExist

def object_list(request, queryset, paginate_by=None, allow_empty=False,
        template_name=None, template_loader=loader,
        extra_context={}, context_processors=None, template_object_name='object'):
    """
    Generic list of objects.

    Templates: ``<app_label>/<model_name>_list.html``
    Context:
        object_list
            list of objects
        is_paginated
            are the results paginated?
        results_per_page
            number of objects per page (if paginated)
        has_next
            is there a next page?
        has_previous
            is there a prev page?
        page
            the current page
        next
            the next page
        previous
            the previous page
        pages
            number of pages, total
        hits
            number of objects, total
    """
    queryset = queryset._clone()
    if paginate_by:
        paginator = ObjectPaginator(queryset, paginate_by)
        page = request.GET.get('page', 1)
        try:
            page = int(page)
            object_list = paginator.get_page(page - 1)
        except (InvalidPage, ValueError):
            if page == 1 and allow_empty:
                object_list = []
            else:
                raise Http404
        c = RequestContext(request, {
            '%s_list' % template_object_name: object_list,
            'is_paginated': paginator.pages > 1,
            'results_per_page': paginate_by,
            'has_next': paginator.has_next_page(page - 1),
            'has_previous': paginator.has_previous_page(page - 1),
            'page': page,
            'next': page + 1,
            'previous': page - 1,
            'pages': paginator.pages,
            'hits' : paginator.hits,
        }, context_processors)
    else:
        c = RequestContext(request, {
            '%s_list' % template_object_name: queryset,
            'is_paginated': False
        }, context_processors)
        if not allow_empty and len(queryset) == 0:
            raise Http404
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    if not template_name:
        model = queryset.model
        template_name = "%s/%s_list.html" % (model._meta.app_label, model._meta.object_name.lower())
    t = template_loader.get_template(template_name)
    return HttpResponse(t.render(c))

def object_detail(request, queryset, object_id=None, slug=None,
        slug_field=None, template_name=None, template_name_field=None,
        template_loader=loader, extra_context={},
        context_processors=None, template_object_name='object'):
    """
    Generic list of objects.

    Templates: ``<app_label>/<model_name>_detail.html``
    Context:
        object
            the object
    """
    model = queryset.model
    if object_id:
        queryset = queryset.filter(pk=object_id)
    elif slug and slug_field:
        queryset = queryset.filter(**{slug_field: slug})
    else:
        raise AttributeError, "Generic detail view must be called with either an object_id or a slug/slug_field."
    try:
        obj = queryset.get()
    except ObjectDoesNotExist:
        raise Http404, "No %s found matching the query" % (model._meta.verbose_name)
    if not template_name:
        template_name = "%s/%s_detail.html" % (model._meta.app_label, model._meta.object_name.lower())
    if template_name_field:
        template_name_list = [getattr(obj, template_name_field), template_name]
        t = template_loader.select_template(template_name_list)
    else:
        t = template_loader.get_template(template_name)
    c = RequestContext(request, {
        template_object_name: obj,
    }, context_processors)
    for key, value in extra_context.items():
        if callable(value):
            c[key] = value()
        else:
            c[key] = value
    response = HttpResponse(t.render(c))
    populate_xheaders(request, response, model, getattr(obj, obj._meta.pk.name))
    return response
