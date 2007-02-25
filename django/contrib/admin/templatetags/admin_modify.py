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

def output_all(form_fields):
    return ''.join([str(f) for f in form_fields])
output_all = register.simple_tag(output_all)

def field_widget(parser, token):
    bits = token.contents.split()
    if len(bits) != 2:
        raise template.TemplateSyntaxError, "%s takes 1 argument" % bits[0]
    return FieldWidgetNode(bits[1])
field_widget = register.tag(field_widget)
