from django import template
from django.contrib.admin.views.main import AdminBoundField
from django.template import loader
from django.utils.text import capfirst
from django.db import models
from django.db.models.fields import Field
from django.db.models.related import BoundRelatedObject
from django.conf import settings
import re

register = template.Library()

word_re = re.compile('[A-Z][a-z]+')

def class_name_to_underscored(name):
    return '_'.join([s.lower() for s in word_re.findall(name)[:-1]])

def include_admin_script(script_path):
    """
    Returns an HTML script element for including a script from the admin
    media url.

    Example usage::

        {% include_admin_script js/calendar.js %}

    could return::

        <script type="text/javascript" src="/media/admin/js/calendar.js">
    """

    return '<script type="text/javascript" src="%s%s"></script>' % (settings.ADMIN_MEDIA_PREFIX, script_path)
include_admin_script = register.simple_tag(include_admin_script)

def submit_row(context):
    opts = context['opts']
    change = context['change']
    is_popup = context['is_popup']
    return {
        'onclick_attrib': (opts.get_ordered_objects() and change
                            and 'onclick="submitOrderForm();"' or ''),
        'show_delete_link': (not is_popup and context['has_delete_permission']
                              and (change or context['show_delete'])),
        'show_save_as_new': not is_popup and change and opts.admin.save_as,
        'show_save_and_add_another': not is_popup and (not opts.admin.save_as or context['add']),
        'show_save_and_continue': not is_popup and context['has_change_permission'],
        'show_save': True
    }
submit_row = register.inclusion_tag('admin/submit_line.html', takes_context=True)(submit_row)

def field_label(bound_field):
    class_names = []
    if isinstance(bound_field.field, models.BooleanField):
        class_names.append("vCheckboxLabel")
        colon = ""
    else:
        if not bound_field.field.blank:
            class_names.append('required')
        if not bound_field.first:
            class_names.append('inline')
        colon = ":"
    class_str = class_names and ' class="%s"' % ' '.join(class_names) or ''
    return '<label for="%s"%s>%s%s</label> ' % (bound_field.element_id, class_str, \
        capfirst(bound_field.field.verbose_name), colon)
field_label = register.simple_tag(field_label)

class FieldWidgetNode(template.Node):
    nodelists = {}
    default = None

    def __init__(self, bound_field_var):
        self.bound_field_var = bound_field_var

    def get_nodelist(cls, klass):
        if not cls.nodelists.has_key(klass):
            try:
                field_class_name = klass.__name__
                template_name = "widget/%s.html" % class_name_to_underscored(field_class_name)
                nodelist = loader.get_template(template_name).nodelist
            except template.TemplateDoesNotExist:
                super_klass = bool(klass.__bases__) and klass.__bases__[0] or None
                if super_klass and super_klass != Field:
                    nodelist = cls.get_nodelist(super_klass)
                else:
                    if not cls.default:
                        cls.default = loader.get_template("widget/default.html").nodelist
                    nodelist = cls.default

            cls.nodelists[klass] = nodelist
            return nodelist
        else:
            return cls.nodelists[klass]
    get_nodelist = classmethod(get_nodelist)

    def render(self, context):
        bound_field = template.resolve_variable(self.bound_field_var, context)

        context.push()
        context['bound_field'] = bound_field

        output = self.get_nodelist(bound_field.field.__class__).render(context)
        context.pop()
        return output

class FieldWrapper(object):
    def __init__(self, field ):
        self.field = field

    def needs_header(self):
        return not isinstance(self.field, models.AutoField)

    def header_class_attribute(self):
        return self.field.blank and ' class="optional"' or ''

    def use_raw_id_admin(self):
        return isinstance(self.field.rel, (models.ManyToOneRel, models.ManyToManyRel)) \
            and self.field.rel.raw_id_admin

class FormFieldCollectionWrapper(object):
    def __init__(self, field_mapping, fields, index):
        self.field_mapping = field_mapping
        self.fields = fields
        self.bound_fields = [AdminBoundField(field, self.field_mapping, field_mapping['original'])
                             for field in self.fields]
        self.index = index

class TabularBoundRelatedObject(BoundRelatedObject):
    def __init__(self, related_object, field_mapping, original):
        super(TabularBoundRelatedObject, self).__init__(related_object, field_mapping, original)
        self.field_wrapper_list = [FieldWrapper(field) for field in self.relation.editable_fields()]

        fields = self.relation.editable_fields()

        self.form_field_collection_wrappers = [FormFieldCollectionWrapper(field_mapping, fields, i)
                                               for (i,field_mapping) in self.field_mappings.items() ]
        self.original_row_needed = max([fw.use_raw_id_admin() for fw in self.field_wrapper_list])
        self.show_url = original and hasattr(self.relation.opts, 'get_absolute_url')

    def template_name(self):
        return "admin/edit_inline_tabular.html"

class StackedBoundRelatedObject(BoundRelatedObject):
    def __init__(self, related_object, field_mapping, original):
        super(StackedBoundRelatedObject, self).__init__(related_object, field_mapping, original)
        fields = self.relation.editable_fields()
        self.field_mappings.fill()
        self.form_field_collection_wrappers = [FormFieldCollectionWrapper(field_mapping ,fields, i)
                                               for (i,field_mapping) in self.field_mappings.items()]
        self.show_url = original and hasattr(self.relation.opts, 'get_absolute_url')

    def template_name(self):
        return "admin/edit_inline_stacked.html"

class EditInlineNode(template.Node):
    def __init__(self, rel_var):
        self.rel_var = rel_var

    def render(self, context):
        relation = template.resolve_variable(self.rel_var, context)
        context.push()
        if relation.field.rel.edit_inline == models.TABULAR:
            bound_related_object_class = TabularBoundRelatedObject
        elif relation.field.rel.edit_inline == models.STACKED:
            bound_related_object_class = StackedBoundRelatedObject
        else:
            bound_related_object_class = relation.field.rel.edit_inline
        original = context.get('original', None)
        bound_related_object = relation.bind(context['form'], original, bound_related_object_class)
        context['bound_related_object'] = bound_related_object
        t = loader.get_template(bound_related_object.template_name())
        output = t.render(context)
        context.pop()
        return output

def output_all(form_fields):
    return ''.join([str(f) for f in form_fields])
output_all = register.simple_tag(output_all)

def auto_populated_field_script(auto_pop_fields, change = False):
    for field in auto_pop_fields:
        t = []
        if change:
            t.append('document.getElementById("id_%s")._changed = true;' % field.name)
        else:
            t.append('document.getElementById("id_%s").onchange = function() { this._changed = true; };' % field.name)

        add_values = ' + " " + '.join(['document.getElementById("id_%s").value' % g for g in field.prepopulate_from])
        for f in field.prepopulate_from:
            t.append('document.getElementById("id_%s").onkeyup = function() {' \
                     ' var e = document.getElementById("id_%s");' \
                     ' if(!e._changed) { e.value = URLify(%s, %s);} }; ' % (
                     f, field.name, add_values, field.maxlength))
    return ''.join(t)
auto_populated_field_script = register.simple_tag(auto_populated_field_script)

def filter_interface_script_maybe(bound_field):
    f = bound_field.field
    if f.rel and isinstance(f.rel, models.ManyToManyRel) and f.rel.filter_interface:
        return '<script type="text/javascript">addEvent(window, "load", function(e) {' \
              ' SelectFilter.init("id_%s", %r, %s, "%s"); });</script>\n' % (
              f.name, f.verbose_name, f.rel.filter_interface-1, settings.ADMIN_MEDIA_PREFIX)
    else:
        return ''
filter_interface_script_maybe = register.simple_tag(filter_interface_script_maybe)

def field_widget(parser, token):
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "%s takes 1 argument" % bits[0]
    return FieldWidgetNode(bits[1])
field_widget = register.tag(field_widget)

def edit_inline(parser, token):
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "%s takes 1 argument" % bits[0]
    return EditInlineNode(bits[1])
edit_inline = register.tag(edit_inline)

def admin_field_line(context, argument_val):
    if isinstance(argument_val, AdminBoundField):
        bound_fields = [argument_val]
    else:
        bound_fields = [bf for bf in argument_val]
    add = context['add']
    change = context['change']

    class_names = ['form-row']
    for bound_field in bound_fields:
        for f in bound_field.form_fields:
            if f.errors():
                class_names.append('errors')
                break

    # Assumes BooleanFields won't be stacked next to each other!
    if isinstance(bound_fields[0].field, models.BooleanField):
        class_names.append('checkbox-row')

    return {
        'add': context['add'],
        'change': context['change'],
        'bound_fields': bound_fields,
        'class_names': " ".join(class_names),
    }
admin_field_line = register.inclusion_tag('admin/field_line.html', takes_context=True)(admin_field_line)
