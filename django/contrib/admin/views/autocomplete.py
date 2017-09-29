from django.http import Http404, JsonResponse
from django.views.generic.list import BaseListView


class AutocompleteJsonView(BaseListView):
    """Handle AutocompleteWidget's AJAX requests for data."""
    paginate_by = 20
    model_admin = None

    def get(self, request, *args, **kwargs):
        """
        Return a JsonResponse with search results of the form:
        {
            results: [{id: "123" text: "foo"}],
            pagination: {more: true}
        }
        """
        if not self.model_admin.get_search_fields(request):
            raise Http404(
                '%s must have search_fields for the autocomplete_view.' %
                type(self.model_admin).__name__
            )
        if not self.has_perm(request):
            return JsonResponse({'error': '403 Forbidden'}, status=403)

        self.term = request.GET.get('term', '')
        self.paginator_class = self.model_admin.paginator
        self.object_list = self.get_queryset()
        context = self.get_context_data()
        return JsonResponse({
            'results': [
                {'id': str(obj.pk), 'text': str(obj)}
                for obj in context['object_list']
            ],
            'pagination': {'more': context['page_obj'].has_next()},
        })

    def get_paginator(self, *args, **kwargs):
        """Use the ModelAdmin's paginator."""
        return self.model_admin.get_paginator(self.request, *args, **kwargs)

    def get_queryset(self):
        """Return queryset based on ModelAdmin.get_search_results()."""
        qs = self.model_admin.get_queryset(self.request)
        qs, search_use_distinct = self.model_admin.get_search_results(self.request, qs, self.term)
        if search_use_distinct:
            qs = qs.distinct()
        return qs

    def has_perm(self, request, obj=None):
        """Check if user has permission to access the related model."""
        return self.model_admin.has_change_permission(request, obj=obj)
