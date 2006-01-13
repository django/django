from django import template
from djang.core import template_loader
from django.utils.html import escape
from django.utils.text import capfirst
from django.utils.functional import curry
from django.contrib.admin.views.stages.modify import AdminBoundField
from django.db.models.fields import BoundField, Field
from django.db.models.related import BoundRelatedObject
from django.db.models import TABULAR, STACKED
from django.db import models
from django.conf.settings import ADMIN_MEDIA_PREFIX
import re

register = template.Library()

word_re = re.compile('[A-Z][a-z]+')

def class_name_to_underscored(name):
    return '_'.join([s.lower() for s in word_re.findall(name)[:-1]])

#@register.simple_tag
def include_admin_script(script_path):
    return '<script type="text/javascript" src="%s%s"></script>' % (ADMIN_MEDIA_PREFIX, script_path)
include_admin_script = register.simple_tag(include_admin_script)

#@register.inclusion_tag('admin/submit_line', takes_context=True)
def submit_row(context, bound_manipulator):
    change = context['change']
    add = context['add']
    show_delete = context['show_delete']
    has_delete_permission = context['has_delete_permission']
    is_popup = context['is_popup']
    return {
        'onclick_attrib': (bound_manipulator.ordered_objects and change
                            and 'onclick="submitOrderForm();"' or ''),
        'show_delete_link': (not is_popup and has_delete_permission
                              and (change or show_delete)),
        'show_save_as_new': not is_popup and change and bound_manipulator.save_as,
        'show_save_and_add_another': not is_popup and (not bound_manipulator.save_as or add),
        'show_save_and_continue': not is_popup,
        'show_save': True
    }
submit_row = register.inclusion_tag('admin/submit_line', takes_context=True)(submit_row)

#@register.simple_tag
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
                template_name = "widget/%s" % \
                    class_name_to_underscored(field_class_name)
                nodelist = template_loader.get_template(template_name).nodelist
            except template.TemplateDoesNotExist:
                super_klass = bool(klass.__bases__) and klass.__bases__[0] or None
                if super_klass and super_klass != Field:
                    nodelist = cls.get_nodelist(super_klass)
                else:
                    if not cls.default:
                        cls.default = template_loader.get_template("widget/default").nodelist
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
         return isinstance(self.field.rel, (models.ManyToOne, models.ManyToMany)) \
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
        return "admin/edit_inline_tabular"

class StackedBoundRelatedObject(BoundRelatedObject):
    def __init__(self, related_object, field_mapping, original):
        super(StackedBoundRelatedObject, self).__init__(related_object, field_mapping, original)
        fields = self.relation.editable_fields()
        self.field_mappings.fill()
        self.form_field_collection_wrappers = [FormFieldCollectionWrapper(field_mapping ,fields, i)
                                               for (i,field_mapping) in self.field_mappings.items()]
        self.show_url = original and hasattr(self.relation.opts, 'get_absolute_url')

    def template_name(self):
        return "admin/edit_inline_stacked"

bound_related_object_overrides = {
    TABULAR: TabularBoundRelatedObject,
    STACKED: StackedBoundRelatedObject,
}

class EditInlineNode(template.Node):
    def __init__(self, rel_var):
        self.rel_var = rel_var

    def render(self, context):
        relation = template.resolve_variable(self.rel_var, context)

        context.push()

        klass = relation.field.rel.edit_inline
        bound_related_object_class = bound_related_object_overrides.get(klass, klass)

        original = context.get('original', None)

        bound_related_object = relation.bind(context['form'], original, bound_related_object_class)
        context['bound_related_object'] = bound_related_object

        t = template_loader.get_template(bound_related_object.template_name())

        output = t.render(context)

        context.pop()
        return output

#@register.simple_tag
def output_all(form_fields):
    return ''.join([str(f) for f in form_fields])
output_all = register.simple_tag(output_all)

#@register.simple_tag
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

#@register.simple_tag
def filter_interface_script_maybe(bound_field):
    f = bound_field.field
    if f.rel and isinstance(f.rel, models.ManyToMany) and f.rel.filter_interface:
       return '<script type="text/javascript">addEvent(window, "load", function(e) {' \
              ' SelectFilter.init("id_%s", "%s", %s, "%s"); });</script>\n' % (
              f.name, f.verbose_name, f.rel.filter_interface-1, ADMIN_MEDIA_PREFIX)
    else:
        return ''
filter_interface_script_maybe = register.simple_tag(filter_interface_script_maybe)

def do_one_arg_tag(node_factory, parser,token):
    tokens = token.contents.split()
    if len(tokens) != 2:
        raise template.TemplateSyntaxError("%s takes 1 argument" % tokens[0])
    return node_factory(tokens[1])

def register_one_arg_tag(node):
    tag_name = class_name_to_underscored(node.__name__)
    parse_func = curry(do_one_arg_tag, node)
    register.tag(tag_name, parse_func)

one_arg_tag_nodes = (
    FieldWidgetNode,
    EditInlineNode,
)

for node in one_arg_tag_nodes:
    register_one_arg_tag(node)

#@register.inclusion_tag('admin/field_line', takes_context=True)
def admin_field_line(context, argument_val):
    if (isinstance(argument_val, BoundField)):
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
admin_field_line = register.inclusion_tag('admin/field_line', takes_context=True)(admin_field_line)

#@register.simple_tag
def object_pk(bound_manip, ordered_obj):
    return bound_manip.get_ordered_object_pk(ordered_obj)

object_pk = register.simple_tag(object_pk)
