from django.db.models.fields import BoundField, BoundFieldLine, BoundFieldSet
from django.db import models

from django.core.extensions import render_to_response
from django.contrib.admin.views.main import url_for_model

use_raw_id_admin = lambda field: isinstance(field.rel, (models.ManyToOne, models.ManyToMany)) and field.rel.raw_id_admin

def get_javascript_imports(opts, auto_populated_fields, ordered_objects, field_sets):
# Put in any necessary JavaScript imports.
    js = ['js/core.js', 'js/admin/RelatedObjectLookups.js']
    if auto_populated_fields:
        js.append('js/urlify.js')
    if opts.has_field_type(models.DateTimeField) or opts.has_field_type(models.TimeField) or opts.has_field_type(models.DateField):
        js.extend(['js/calendar.js', 'js/admin/DateTimeShortcuts.js'])
    if ordered_objects:
        js.extend(['js/getElementsBySelector.js', 'js/dom-drag.js' , 'js/admin/ordering.js'])
    if opts.admin.js:
        js.extend(opts.admin.js)
    seen_collapse = False
    for field_set in field_sets:
        if not seen_collapse and 'collapse' in field_set.classes:
            seen_collapse = True
            js.append('js/admin/CollapsedFieldsets.js' )

        for field_line in field_set:
            try:
                for f in field_line:
                    if f.rel and isinstance(f, models.ManyToManyField) and f.rel.filter_interface:
                        js.extend(['js/SelectBox.js' , 'js/SelectFilter2.js'])
                        raise StopIteration
            except StopIteration:
                break
    return js

class AdminBoundField(BoundField):
    def __init__(self, field, field_mapping, original):
        super(AdminBoundField, self).__init__(field, field_mapping, original)

        self.element_id = self.form_fields[0].get_id()
        self.has_label_first = not isinstance(self.field, models.BooleanField)
        self.raw_id_admin = use_raw_id_admin(field)
        self.is_date_time = isinstance(field, models.DateTimeField)
        self.is_file_field = isinstance(field, models.FileField)
        self.needs_add_label = field.rel and isinstance(field.rel, models.ManyToOne) or isinstance(field.rel, models.ManyToMany) and field.rel.to._meta.admin
        self.hidden = isinstance(self.field, models.AutoField)
        self.first = False

        classes = []
        if self.raw_id_admin:
            classes.append('nowrap')
        if max([bool(f.errors()) for f in self.form_fields]):
            classes.append('error')
        if classes:
            self.cell_class_attribute = ' class="%s" ' % ' '.join(classes)
        self._repr_filled = False

        if field.rel:
            self.related_url = url_for_model(field.rel.to)

    def _fetch_existing_display(self, func_name):
        class_dict = self.original.__class__.__dict__
        func = class_dict.get(func_name)
        return func(self.original)

    def _fill_existing_display(self):
        if getattr(self, '_display_filled', False):
            return
        # HACK
        if isinstance(self.field.rel, models.ManyToOne):
             func_name = 'get_%s' % self.field.name
             self._display = self._fetch_existing_display(func_name)
        elif isinstance(self.field.rel, models.ManyToMany):
            func_name = 'get_%s_list' % self.field.rel.singular
            self._display =  ", ".join([str(obj) for obj in self._fetch_existing_display(func_name)])
        self._display_filled = True

    def existing_display(self):
        self._fill_existing_display()
        return self._display

    def __repr__(self):
        return repr(self.__dict__)

    def html_error_list(self):
        return " ".join([form_field.html_error_list() for form_field in self.form_fields if form_field.errors])

    def original_url(self):
        if self.is_file_field and self.original and self.field.attname:
            url_method = getattr(self.original, 'get_%s_url' % self.field.attname)
            if callable(url_method):
                return url_method()
        return ''

class AdminBoundFieldLine(BoundFieldLine):
    def __init__(self, field_line, field_mapping, original):
        super(AdminBoundFieldLine, self).__init__(field_line, field_mapping, original, AdminBoundField)
        for bound_field in self:
            bound_field.first = True
            break

class AdminBoundFieldSet(BoundFieldSet):
    def __init__(self, field_set, field_mapping, original):
        super(AdminBoundFieldSet, self).__init__(field_set, field_mapping, original, AdminBoundFieldLine)

class BoundManipulator(object):
    def __init__(self, model, manipulator, field_mapping):
        self.model = model
        self.opts = model._meta
        self.inline_related_objects = self.opts.get_followed_related_objects(manipulator.follow)
        self.original = hasattr(manipulator, 'original_object') and manipulator.original_object or None
        self.bound_field_sets = [field_set.bind(field_mapping, self.original, AdminBoundFieldSet)
                                 for field_set in self.opts.admin.get_field_sets(self.opts)]
        self.ordered_objects = self.opts.get_ordered_objects()[:]

class AdminBoundManipulator(BoundManipulator):
    def __init__(self, model, manipulator, field_mapping):
        super(AdminBoundManipulator, self).__init__(model, manipulator, field_mapping)
        field_sets = self.opts.admin.get_field_sets(self.opts)

        self.auto_populated_fields = [f for f in self.opts.fields if f.prepopulate_from]
        self.javascript_imports = get_javascript_imports(self.opts, self.auto_populated_fields, self.ordered_objects, field_sets);

        self.coltype = self.ordered_objects and 'colMS' or 'colM'
        self.has_absolute_url = hasattr(model, 'get_absolute_url')
        self.form_enc_attrib = self.opts.has_field_type(models.FileField) and \
                                'enctype="multipart/form-data" ' or ''

        self.first_form_field_id = self.bound_field_sets[0].bound_field_lines[0].bound_fields[0].form_fields[0].get_id();
        self.ordered_object_pk_names = [o.pk.name for o in self.ordered_objects]

        opts = self.opts
        self.save_on_top = opts.admin.save_on_top
        self.save_as = opts.admin.save_as

        self.content_type_id = opts.get_content_type_id()
        self.verbose_name_plural = opts.verbose_name_plural
        self.verbose_name = opts.verbose_name
        self.object_name = opts.object_name

    def get_ordered_object_pk(self, ordered_obj):
        for name in self.ordered_object_pk_names:
            if hasattr(ordered_obj, name):
                return str(getattr(ordered_obj, name))
        return ""

def render_change_form(model, manipulator, app_label, context, add=False, change=False, show_delete=False, form_url=''):
    opts = model._meta
    extra_context = {
        'add': add,
        'change': change,
        'bound_manipulator': AdminBoundManipulator(model, manipulator, context['form']),
        'has_delete_permission': context['perms'][app_label][opts.get_delete_permission()],
        'form_url': form_url,
        'app_label': app_label,
    }
    context.update(extra_context)
    return render_to_response(["admin/%s/%s/change_form" % (app_label, opts.object_name.lower() ),
                               "admin/%s/change_form" % app_label ,
                               "admin/change_form"], context_instance=context)
