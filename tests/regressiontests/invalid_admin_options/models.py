"""
Admin options

Test invalid and valid admin options to make sure that
model validation is working properly. 
"""

from django.db import models
model_errors = ""

class ListDisplayBadOne(models.Model):
    "Test list_display, list_display must be a list or tuple"
    first_name = models.CharField(maxlength=30)

    class Admin:
        list_display = 'first_name'

model_errors += """invalid_admin_options.listdisplaybadone: "admin.list_display", if given, must be set to a list or tuple.
"""

class ListDisplayBadTwo(models.Model):
    "Test list_display, list_display items must be attributes, methods or properties."
    first_name = models.CharField(maxlength=30)

    class Admin:
        list_display = ['first_name','nonexistent']

model_errors += """invalid_admin_options.listdisplaybadtwo: "admin.list_display" refers to 'nonexistent', which isn't an attribute, method or property.
"""        
class ListDisplayBadThree(models.Model):
    "Test list_display, list_display items can not be a ManyToManyField."
    first_name = models.CharField(maxlength=30)
    nick_names = models.ManyToManyField('ListDisplayGood')

    class Admin:
        list_display = ['first_name','nick_names']
        
model_errors += """invalid_admin_options.listdisplaybadthree: "admin.list_display" doesn't support ManyToManyFields ('nick_names').
""" 
      
class ListDisplayGood(models.Model):
    "Test list_display, Admin list_display can be a attribute, method or property."
    first_name = models.CharField(maxlength=30)
    
    def _last_name(self):
        return self.first_name
    last_name = property(_last_name)
    
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    class Admin:
        list_display = ['first_name','last_name','full_name']
       
class ListDisplayLinksBadOne(models.Model):
    "Test list_display_links, item must be included in list_display."
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    
    class Admin:
        list_display = ['last_name']
        list_display_links = ['first_name']

model_errors += """invalid_admin_options.listdisplaylinksbadone: "admin.list_display_links" refers to 'first_name', which is not defined in "admin.list_display".
"""

class ListDisplayLinksBadTwo(models.Model):
    "Test list_display_links, must be a list or tuple."
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    
    class Admin:
        list_display = ['first_name','last_name']
        list_display_links = 'last_name'    

model_errors += """invalid_admin_options.listdisplaylinksbadtwo: "admin.list_display_links", if given, must be set to a list or tuple.
"""

# TODO: Fix list_display_links validation or remove the check for list_display
## This is failing but the validation which should fail is not.
#class ListDisplayLinksBadThree(models.Model):
#    "Test list_display_links, must define list_display to use list_display_links."
#    first_name = models.CharField(maxlength=30)
#    last_name = models.CharField(maxlength=30)
#    
#    class Admin:
#        list_display_links = ('first_name',)
#
#model_errors += """invalid_admin_options.listdisplaylinksbadthree: "admin.list_display" must be defined for "admin.list_display_links" to be used.
#"""
        
class ListDisplayLinksGood(models.Model):
    "Test list_display_links, Admin list_display_list can be a attribute, method or property."
    first_name = models.CharField(maxlength=30)
    
    def _last_name(self):
        return self.first_name
    last_name = property(_last_name)
    
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    class Admin:
        list_display = ['first_name','last_name','full_name']
        list_display_links = ['first_name','last_name','full_name']

class ListFilterBadOne(models.Model):
    "Test list_filter, must be a list or tuple."
    first_name = models.CharField(maxlength=30)
    
    class Admin:
        list_filter = 'first_name'     

model_errors += """invalid_admin_options.listfilterbadone: "admin.list_filter", if given, must be set to a list or tuple.
"""

class ListFilterBadTwo(models.Model):
    "Test list_filter, must be a field not a property or method."
    first_name = models.CharField(maxlength=30)
    
    def _last_name(self):
        return self.first_name
    last_name = property(_last_name)
    
    def full_name(self):
        return "%s %s" % (self.first_name, self.last_name)

    class Admin:
        list_filter = ['first_name','last_name','full_name']

model_errors += """invalid_admin_options.listfilterbadtwo: "admin.list_filter" refers to 'last_name', which isn't a field.
invalid_admin_options.listfilterbadtwo: "admin.list_filter" refers to 'full_name', which isn't a field.
"""

class DateHierarchyBadOne(models.Model):
    "Test date_hierarchy, must be a date or datetime field."
    first_name = models.CharField(maxlength=30)
    birth_day = models.DateField()
    
    class Admin:
        date_hierarchy = 'first_name'
        
# TODO: Date Hierarchy needs to check if field is a date/datetime field.
#model_errors += """invalid_admin_options.datehierarchybadone: "admin.date_hierarchy" refers to 'first_name', which isn't a date field or datetime field.
#"""

class DateHierarchyBadTwo(models.Model):
    "Test date_hieracrhy, must be a field."
    first_name = models.CharField(maxlength=30)
    birth_day = models.DateField()
    
    class Admin:
        date_hierarchy = 'nonexistent'          

model_errors += """invalid_admin_options.datehierarchybadtwo: "admin.date_hierarchy" refers to 'nonexistent', which isn't a field.
"""

class DateHierarchyGood(models.Model):
    "Test date_hieracrhy, must be a field."
    first_name = models.CharField(maxlength=30)
    birth_day = models.DateField()
    
    class Admin:
        date_hierarchy = 'birth_day' 
      
class SearchFieldsBadOne(models.Model):
    "Test search_fields, must be a list or tuple."
    first_name = models.CharField(maxlength=30)
    
    class Admin:
        search_fields = ('nonexistent')         

# TODO: Add search_fields validation
#model_errors += """invalid_admin_options.seacrhfieldsbadone: "admin.search_fields", if given, must be set to a list or tuple.
#"""
      
class SearchFieldsBadTwo(models.Model):
    "Test search_fields, must be a field."
    first_name = models.CharField(maxlength=30)

    def _last_name(self):
        return self.first_name
    last_name = property(_last_name)
    
    class Admin:
        search_fields = ['first_name','last_name']         

# TODO: Add search_fields validation
#model_errors += """invalid_admin_options.seacrhfieldsbadone: "admin.search_fields" refers to 'last_name', which isn't a field.
#"""

class SearchFieldsGood(models.Model):
    "Test search_fields, must be a list or tuple."
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    
    class Admin:
        search_fields = ['first_name','last_name']


class JsBadOne(models.Model):
    "Test js, must be a list or tuple"
    name = models.CharField(maxlength=30)
    
    class Admin:
        js = 'test.js'
        
# TODO: Add a js validator
#model_errors += """invalid_admin_options.jsbadone: "admin.js", if given, must be set to a list or tuple.
#"""

class SaveAsBad(models.Model):
    "Test save_as, should be True or False"
    name = models.CharField(maxlength=30)
    
    class Admin:
        save_as = 'not True or False'

# TODO: Add a save_as validator.       
#model_errors += """invalid_admin_options.saveasbad: "admin.save_as", if given, must be set to True or False.
#"""

class SaveOnTopBad(models.Model):
    "Test save_on_top, should be True or False"
    name = models.CharField(maxlength=30)
    
    class Admin:
        save_on_top = 'not True or False'

# TODO: Add a save_on_top validator.       
#model_errors += """invalid_admin_options.saveontopbad: "admin.save_on_top", if given, must be set to True or False.
#"""

class ListSelectRelatedBad(models.Model):
    "Test list_select_related, should be True or False"
    name = models.CharField(maxlength=30)
    
    class Admin:
        list_select_related = 'not True or False'

# TODO: Add a list_select_related validator.       
#model_errors += """invalid_admin_options.listselectrelatebad: "admin.list_select_related", if given, must be set to True or False.
#"""

class ListPerPageBad(models.Model):
    "Test list_per_page, should be a positive integer value."
    name = models.CharField(maxlength=30)
    
    class Admin:
        list_per_page = 89.3

# TODO: Add a list_per_page validator.       
#model_errors += """invalid_admin_options.listperpagebad: "admin.list_per_page", if given, must be a positive integer.
#"""

class FieldsBadOne(models.Model):
    "Test fields, should be a tuple"
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    
    class Admin:
        fields = 'not a tuple'

# TODO: Add a fields validator.       
#model_errors += """invalid_admin_options.fieldsbadone: "admin.fields", if given, must be a tuple.
#"""

class FieldsBadTwo(models.Model):
    """Test fields, 'fields' dict option is required."""
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    
    class Admin:
        fields = ('Name', {'description': 'this fieldset needs fields'})
        
# TODO: Add a fields validator.       
#model_errors += """invalid_admin_options.fieldsbadtwo: "admin.fields" each fieldset must include a 'fields' dict.
#"""

class FieldsBadThree(models.Model):
    """Test fields, 'classes' and 'description' are the only allowable extra dict options."""
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    
    class Admin:
        fields = ('Name', {'fields': ('first_name','last_name'),'badoption': 'verybadoption'})

# TODO: Add a fields validator.       
#model_errors += """invalid_admin_options.fieldsbadthree: "admin.fields" fieldset options must be either 'classes' or 'description'.
#"""

class FieldsGood(models.Model):
    "Test fields, working example"
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    birth_day = models.DateField()
    
    class Admin:
        fields = (
                  ('Name', {'fields': ('first_name','last_name'),'classes': 'collapse'}),
                  (None, {'fields': ('birth_day',),'description': 'enter your b-day'})
                  )
                  
class OrderingBad(models.Model):
    "Test ordering, must be a field."
    first_name = models.CharField(maxlength=30)
    last_name = models.CharField(maxlength=30)
    
    class Admin:
        ordering = 'nonexistent'

# TODO: Add a ordering validator.       
#model_errors += """invalid_admin_options.orderingbad: "admin.ordering" refers to 'nonexistent', which isn't a field.
#"""

## TODO: Add a manager validator, this should fail gracefully.
#class ManagerBad(models.Model):
#    "Test manager, must be a manager object."
#    first_name = models.CharField(maxlength=30)
#    
#    class Admin:
#        manager = 'nonexistent'
#       
#model_errors += """invalid_admin_options.managerbad: "admin.manager" refers to 'nonexistent', which isn't a Manager().
#"""
