from django.core import template, template_loader, meta
from django.core.template_loader import render_to_string
from django.conf.settings import ADMIN_MEDIA_PREFIX
from django.utils.text import capfirst
from django.utils.html import escape
from django.utils.functional import curry

from django.views.admin.main import AdminBoundField
import re

class IncludeAdminScriptNode(template.Node):
    def __init__(self, var):
        self.var = var
 
    def render(self, context):
        resolved = template.resolve_variable(self.var, context)
        return '<script type="text/javascript" src="%s%s"></script>' % \
            (ADMIN_MEDIA_PREFIX, resolved)
          
class SubmitRowNode(template.Node):
    def __init__(self):
        pass

    def render(self, context):        
        change = context['change']
	add = context['add']
	show_delete = context['show_delete']
	ordered_objects = context['ordered_objects']
 	save_as = context['save_as']
	has_delete_permission = context['has_delete_permission']
        is_popup = context['is_popup']
	  
        
        output = render_to_string('admin_submit_line', {
	    'onclick_attrib' : (ordered_objects and change 
                                and 'onclick="submitOrderForm();"' or ''), 
            'show_delete_link' : (not is_popup and has_delete_permission 
                                  and (change or show_delete)), 
            'show_save_as_new' : not is_popup and change and save_as,
            'show_save_and_add_another': not is_popup and (not save_as or add),
            'show_save_and_continue': not is_popup,
            'show_save': True
          }, context);
        context.pop() 
        return output;
#	  t = ['<div class="submit-row">']
	  
#	  if not is_popup:
#	  	if has_delete_permission and (change or show_delete):
#	      	   t.append('<p class="float-left"><a href="delete/" class="deletelink">Delete</a></p>')
#	        if change and save_as:
#		   t.append('<input type="submit" value="Save as new" name="_saveasnew" %s/>' %  onclick_attrib)
#                if (not save_as or add):
#		   t.append('<input type="submit" value="Save and add another" name="_addanother" %s/>' %  onclick_attrib)
#	        t.append('<input type="submit" value="Save and continue editing" name="_continue" %s/>' %  onclick_attrib )
#	  t.append('<input type="submit" value="Save" class="default" %s/>' %  onclick_attrib)
#	  t.append('</div>\n')
	 
#	  return ''.join(t)




class AdminFieldBoundNode(template.Node):
    def __init__(self, argument):
        self.argument = argument
    
    def render(self, context):
        argument_val = template.resolve_variable(self.argument, context)
        if (isinstance(argument_val, list)):
            bound_fields = argument_val 
        else:
            bound_fields = [argument_val]
        add = context['add']
        change = context['change']
        
        context.push()
        context['bound_fields'] = bound_fields
        context['class_names'] = " ".join(self.get_class_names(bound_fields))
        t = template_loader.get_template("admin_field")
        output =  t.render(context)
        context.pop()
          
        return output

    def get_class_names(self, bound_fields):

	class_names = ['form-row']
	for bound_field in bound_fields: 
            for f in bound_field.form_fields:
                if f.errors():
                    class_names.append('errors')
                    break
	  
	# Assumes BooleanFields won't be stacked next to each other!
	if isinstance(bound_fields[0].field, meta.BooleanField):
	    class_names.append('checkbox-row')
	  
        return class_names
       
class FieldWidgetNode(template.Node):
    def __init__(self, bound_field_var):
        self.bound_field_var = bound_field_var

    def render(self, context):
        bound_field = template.resolve_variable(self.bound_field_var, context)
        add = context['add']
        change = context['change']
        
        context.push()
        context['bound_field'] = bound_field
        t = template_loader.get_template("admin_field_widget")
        output =  t.render(context)
        context.pop()
          
        return output

        

class FieldWrapper(object):
    def __init__(self, field ):
        self.field = field

    def needs_header(self):
        return not isinstance(self.field, meta.AutoField)

    def header_class_attribute(self):
        return self.field.blank and ' class="optional"' or ''

    def use_raw_id_admin(self):
         return isinstance(self.field.rel, (meta.ManyToOne, meta.ManyToMany)) \
                and self.field.rel.raw_id_admin

class FormFieldCollectionWrapper(object):
    def __init__(self, obj, fields):
        self.obj = obj
        self.fields = fields
        self.bound_fields = [ AdminBoundField(field, obj['original'],  True, self.obj) for field in self.fields ]

    def showurl(self):
        return False

class EditInlineNode(template.Node):
    def __init__(self, rel_var):
        self.rel_var = rel_var
    
    def render(self, context):
        relation = template.resolve_variable(self.rel_var, context)
        add, change = context['add'], context['change']
        
        context.push()

        self.fill_context(relation, add, change, context)
        
        t = template_loader.get_template(relation.field.rel.edit_inline)
        
        output = t.render(context)
         
        context.pop()
        return output

       
    def fill_context(self, relation, add, change, context):
        field_wrapper_list = relation.editable_fields(FieldWrapper)

        var_name = relation.opts.object_name.lower()
        
        form = template.resolve_variable('form', context)
        form_field_collections = form[relation.opts.module_name]
        fields = relation.editable_fields()
        form_field_collection_wrapper_list = [FormFieldCollectionWrapper(o,fields) for o in form_field_collections] 
   
        context['field_wrapper_list'] = field_wrapper_list
        context['form_field_collection_wrapper_list'] = form_field_collection_wrapper_list 
        context['num_headers'] = len(field_wrapper_list)
        context['original_row_needed'] = max([fw.use_raw_id_admin() for fw in field_wrapper_list]) 
#        context['name_prefix'] = "%s." % (var_name,)
   
class FieldLabelNode(template.Node):
    def __init__(self, bound_field_var):
        self.bound_field_var = bound_field_var
        
    def render(self, context):
        bound_field = template.resolve_variable(self.bound_field_var, context)
        class_names = []
        if isinstance(bound_field.field, meta.BooleanField):
            class_names.append("vCheckboxLabel")
        else:
            if not bound_field.field.blank:
                class_names.append('required')
            if not bound_field.first:
                class_names.append('inline')
        
        class_str = class_names and ' class="%s"' % ' '.join(class_names) or ''
        return '<label for="%s"%s>%s:</label> ' % (bound_field.element_id, class_str, capfirst(bound_field.field.verbose_name) )

class OutputAllNode(template.Node):
    def __init__(self, form_fields_var):
        self.form_fields_var = form_fields_var
    
    def render(self, context):
        form_fields = template.resolve_variable(self.form_fields_var, context)
        return ''.join([str(f) for f in form_fields])

class AutoPopulatedFieldScriptNode(template.Node):
    def __init__(self, auto_pop_var):
        self.auto_pop_var = auto_pop_var

    def render(self,context):
        auto_pop_fields = template.resolve_variable(self.auto_pop_var, context)
        change = context['change']
        for field in auto_pop_fields:
            t = []
            if change:
                t.append('document.getElementById("id_%s")._changed = true;' % field.name )
            else: 
                t.append('document.getElementById("id_%s").onchange = function() { this._changed = true; };' % field.name)

            add_values = ' + " " + '.join(['document.getElementById("id_%s").value' % g for g in field.prepopulate_from])
            for f in field.prepopulate_from:
                t.append('document.getElementById("id_%s").onkeyup = function() { var e = document.getElementById("id_%s"); if(e._changed) { e.value = URLify(%s, %s);} } ' % (f, field.name, add_values, field.maxlength) )

        return ''.join(t)

class FilterInterfaceScriptMaybeNode(template.Node):
    def __init__(self, bound_field_var):
       self.bound_field_var = bound_field_var

    def render(self, context):
        bound_field = template.resolve_variable(self.bound_field_var, context)
        f = bound_field.field 
        if f.rel and isinstance(f.rel, meta.ManyToMany) and f.rel.filter_interface:
           return '<script type="text/javascript">addEvent(window, "load", function(e) { SelectFilter.init("id_%s", "%s", %s, %r); });</script>\n' % (f.name, f.verbose_name, f.rel.filter_interface-1, ADMIN_MEDIA_PREFIX) 
        else: 
            return ''

     


def do_submit_row(parser, token):
    return SubmitRowNode()


def do_one_arg_tag(node_factory, parser,token):
    tokens = token.contents.split()
    if len(tokens) != 2:
        raise template.TemplateSyntaxError("%s takes 1 argument" % tokens[0])
    return node_factory(tokens[1]) 


one_arg_tag_nodes = [
    IncludeAdminScriptNode,
    AdminFieldBoundNode,
    FieldLabelNode,
    FieldWidgetNode, 
    OutputAllNode,
    EditInlineNode, 
    AutoPopulatedFieldScriptNode,
    FilterInterfaceScriptMaybeNode,
]

word = re.compile('[A-Z][a-z]+')
def register_one_arg_tag(node):
    tag_name = '_'.join([ s.lower() for s in word.findall(node.__name__)[:-1] ])
    parse_func = curry(do_one_arg_tag, node)
    template.register_tag(tag_name, parse_func)

 

for node in one_arg_tag_nodes:
    register_one_arg_tag(node)    

template.register_tag('submit_row', do_submit_row )
