

class ChangeList(BaseView):
    """
    The admin change list view.

    Templates::
        ``<app_label>/<model_name>/change_list.html``
        ``<app_label>/change_list.html``
        ``admin/change_list.html``
    Context::
        object_list
        
        paginator

        page_obj
    """
    def __init__(self, queryset=None, fields=None, filter_fields=None,
                 search_fields=None, date_hierarchy=None):
        self.fields = fields
        self.filter_fields = filter_fields
        self.search_fields = search_fields
        self.date_hierarchy = date_hierarchy
        super(ChangeList, self).__init__(queryset)

    def __call__(self, request):
        pass

    def get_template(self, request, obj=None):
        opts = self.model._meta
        template_path = [
            'admin/%s/%s/change_list.html' % (app_label, opts.object_name.lower()),
            'admin/%s/change_list.html' % app_label,
            'admin/change_list.html'
        ]
        return loader.find_template(template_path)

class EditView(BaseDetailView):
    def get_template(self, request, obj=None):
        opts = self.model._meta
        template_path = [
            'admin/%s/%s/change_list.html' % (app_label, opts.object_name.lower()),
            'admin/%s/change_list.html' % app_label,
            'admin/change_list.html'
        ]
        return loader.find_template(template_path)

class DeleteView(BaseDetailView):
    pass

class HistoryView(BaseDetailView):
    pass