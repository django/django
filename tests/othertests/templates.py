from django.core import template, template_loader

# Helper objects for template tests
class SomeClass:
    def __init__(self):
        self.otherclass = OtherClass()

    def method(self):
        return "SomeClass.method"

    def method2(self, o):
        return o

class OtherClass:
    def method(self):
        return "OtherClass.method"

# SYNTAX --
# 'template_name': ('template contents', 'context dict', 'expected string output' or Exception class)
TEMPLATE_TESTS = {

    ### BASIC SYNTAX ##########################################################

    # Plain text should go through the template parser untouched
    'basic-syntax01': ("something cool", {}, "something cool"),

    # Variables should be replaced with their value in the current context
    'basic-syntax02': ("{{ headline }}", {'headline':'Success'}, "Success"),

    # More than one replacement variable is allowed in a template
    'basic-syntax03': ("{{ first }} --- {{ second }}", {"first" : 1, "second" : 2}, "1 --- 2"),

    # Fail silently when a variable is not found in the current context
    'basic-syntax04': ("as{{ missing }}df", {}, "asdf"),

    # A variable may not contain more than one word
    'basic-syntax06': ("{{ multi word variable }}", {}, template.TemplateSyntaxError),

    # Raise TemplateSyntaxError for empty variable tags
    'basic-syntax07': ("{{ }}",        {}, template.TemplateSyntaxError),
    'basic-syntax08': ("{{        }}", {}, template.TemplateSyntaxError),

    # Attribute syntax allows a template to call an object's attribute
    'basic-syntax09': ("{{ var.method }}", {"var": SomeClass()}, "SomeClass.method"),

    # Multiple levels of attribute access are allowed
    'basic-syntax10': ("{{ var.otherclass.method }}", {"var": SomeClass()}, "OtherClass.method"),

    # Fail silently when a variable's attribute isn't found
    'basic-syntax11': ("{{ var.blech }}", {"var": SomeClass()}, ""),

    # Raise TemplateSyntaxError when trying to access a variable beginning with an underscore
    'basic-syntax12': ("{{ var.__dict__ }}", {"var": SomeClass()}, template.TemplateSyntaxError),

    # Raise TemplateSyntaxError when trying to access a variable containing an illegal character
    'basic-syntax13': ("{{ va>r }}", {}, template.TemplateSyntaxError),
    'basic-syntax14': ("{{ (var.r) }}", {}, template.TemplateSyntaxError),
    'basic-syntax15': ("{{ sp%am }}", {}, template.TemplateSyntaxError),
    'basic-syntax16': ("{{ eggs! }}", {}, template.TemplateSyntaxError),
    'basic-syntax17': ("{{ moo? }}", {}, template.TemplateSyntaxError),

    # Attribute syntax allows a template to call a dictionary key's value
    'basic-syntax18': ("{{ foo.bar }}", {"foo" : {"bar" : "baz"}}, "baz"),

    # Fail silently when a variable's dictionary key isn't found
    'basic-syntax19': ("{{ foo.spam }}", {"foo" : {"bar" : "baz"}}, ""),

    # Fail silently when accessing a non-simple method
    'basic-syntax20': ("{{ var.method2 }}", {"var": SomeClass()}, ""),

    # Basic filter usage
    'basic-syntax21': ("{{ var|upper }}", {"var": "Django is the greatest!"}, "DJANGO IS THE GREATEST!"),

    # Chained filters
    'basic-syntax22': ("{{ var|upper|lower }}", {"var": "Django is the greatest!"}, "django is the greatest!"),

    # Raise TemplateSyntaxError for space between a variable and filter pipe
    'basic-syntax23': ("{{ var |upper }}", {}, template.TemplateSyntaxError),

    # Raise TemplateSyntaxError for space after a filter pipe
    'basic-syntax24': ("{{ var| upper }}", {}, template.TemplateSyntaxError),

    # Raise TemplateSyntaxError for a nonexistent filter
    'basic-syntax25': ("{{ var|does_not_exist }}", {}, template.TemplateSyntaxError),

    # Raise TemplateSyntaxError when trying to access a filter containing an illegal character
    'basic-syntax26': ("{{ var|fil(ter) }}", {}, template.TemplateSyntaxError),

    # Raise TemplateSyntaxError for invalid block tags
    'basic-syntax27': ("{% nothing_to_see_here %}", {}, template.TemplateSyntaxError),

    # Raise TemplateSyntaxError for empty block tags
    'basic-syntax28': ("{% %}", {}, template.TemplateSyntaxError),

    # Chained filters, with an argument to the first one
    'basic-syntax29': ('{{ var|removetags:"b i"|upper|lower }}', {"var": "<b><i>Yes</i></b>"}, "yes"),

    ### IF TAG ################################################################
    'if-tag01': ("{% if foo %}yes{% else %}no{% endif %}", {"foo": True}, "yes"),
    'if-tag02': ("{% if foo %}yes{% else %}no{% endif %}", {"foo": False}, "no"),
    'if-tag03': ("{% if foo %}yes{% else %}no{% endif %}", {}, "no"),

    ### COMMENT TAG ###########################################################
    'comment-tag01': ("{% comment %}this is hidden{% endcomment %}hello", {}, "hello"),
    'comment-tag02': ("{% comment %}this is hidden{% endcomment %}hello{% comment %}foo{% endcomment %}", {}, "hello"),

    ### FOR TAG ###############################################################
    'for-tag01': ("{% for val in values %}{{ val }}{% endfor %}", {"values": [1, 2, 3]}, "123"),
    'for-tag02': ("{% for val in values reversed %}{{ val }}{% endfor %}", {"values": [1, 2, 3]}, "321"),

    ### IFEQUAL TAG ###########################################################
    'ifequal01': ("{% ifequal a b %}yes{% endifequal %}", {"a": 1, "b": 2}, ""),
    'ifequal02': ("{% ifequal a b %}yes{% endifequal %}", {"a": 1, "b": 1}, "yes"),
    'ifequal03': ("{% ifequal a b %}yes{% else %}no{% endifequal %}", {"a": 1, "b": 2}, "no"),
    'ifequal04': ("{% ifequal a b %}yes{% else %}no{% endifequal %}", {"a": 1, "b": 1}, "yes"),
    'ifequal05': ("{% ifequal a 'test' %}yes{% else %}no{% endifequal %}", {"a": "test"}, "yes"),
    'ifequal06': ("{% ifequal a 'test' %}yes{% else %}no{% endifequal %}", {"a": "no"}, "no"),
    'ifequal07': ('{% ifequal a "test" %}yes{% else %}no{% endifequal %}', {"a": "test"}, "yes"),
    'ifequal08': ('{% ifequal a "test" %}yes{% else %}no{% endifequal %}', {"a": "no"}, "no"),
    'ifequal09': ('{% ifequal a "test" %}yes{% else %}no{% endifequal %}', {}, "no"),
    'ifequal10': ('{% ifequal a b %}yes{% else %}no{% endifequal %}', {}, "yes"),

    ### IFNOTEQUAL TAG ########################################################
    'ifnotequal01': ("{% ifnotequal a b %}yes{% endifnotequal %}", {"a": 1, "b": 2}, "yes"),
    'ifnotequal02': ("{% ifnotequal a b %}yes{% endifnotequal %}", {"a": 1, "b": 1}, ""),
    'ifnotequal03': ("{% ifnotequal a b %}yes{% else %}no{% endifnotequal %}", {"a": 1, "b": 2}, "yes"),
    'ifnotequal04': ("{% ifnotequal a b %}yes{% else %}no{% endifnotequal %}", {"a": 1, "b": 1}, "no"),

    ### INHERITANCE ###########################################################

    # Standard template with no inheritance
    'inheritance01': ("1{% block first %}_{% endblock %}3{% block second %}_{% endblock %}", {}, '1_3_'),

    # Standard two-level inheritance
    'inheritance02': ("{% extends 'inheritance01' %}{% block first %}2{% endblock %}{% block second %}4{% endblock %}", {}, '1234'),

    # Three-level with no redefinitions on third level
    'inheritance03': ("{% extends 'inheritance02' %}", {}, '1234'),

    # Two-level with no redefinitions on second level
    'inheritance04': ("{% extends 'inheritance01' %}", {}, '1_3_'),

    # Two-level with double quotes instead of single quotes
    'inheritance05': ('{% extends "inheritance02" %}', {}, '1234'),

    # Three-level with variable parent-template name
    'inheritance06': ("{% extends foo %}", {'foo': 'inheritance02'}, '1234'),

    # Two-level with one block defined, one block not defined
    'inheritance07': ("{% extends 'inheritance01' %}{% block second %}5{% endblock %}", {}, '1_35'),

    # Three-level with one block defined on this level, two blocks defined next level
    'inheritance08': ("{% extends 'inheritance02' %}{% block second %}5{% endblock %}", {}, '1235'),

    # Three-level with second and third levels blank
    'inheritance09': ("{% extends 'inheritance04' %}", {}, '1_3_'),

    # Three-level with space NOT in a block -- should be ignored
    'inheritance10': ("{% extends 'inheritance04' %}      ", {}, '1_3_'),

    # Three-level with both blocks defined on this level, but none on second level
    'inheritance11': ("{% extends 'inheritance04' %}{% block first %}2{% endblock %}{% block second %}4{% endblock %}", {}, '1234'),

    # Three-level with this level providing one and second level providing the other
    'inheritance12': ("{% extends 'inheritance07' %}{% block first %}2{% endblock %}", {}, '1235'),

    # Three-level with this level overriding second level
    'inheritance13': ("{% extends 'inheritance02' %}{% block first %}a{% endblock %}{% block second %}b{% endblock %}", {}, '1a3b'),

    # A block defined only in a child template shouldn't be displayed
    'inheritance14': ("{% extends 'inheritance01' %}{% block newblock %}NO DISPLAY{% endblock %}", {}, '1_3_'),

    # A block within another block
    'inheritance15': ("{% extends 'inheritance01' %}{% block first %}2{% block inner %}inner{% endblock %}{% endblock %}", {}, '12inner3_'),

    # A block within another block (level 2)
    'inheritance16': ("{% extends 'inheritance15' %}{% block inner %}out{% endblock %}", {}, '12out3_'),

    # {% load %} tag (parent -- setup for exception04)
    'inheritance17': ("{% load testtags %}{% block first %}1234{% endblock %}", {}, '1234'),

    # {% load %} tag (standard usage, without inheritance)
    'inheritance18': ("{% load testtags %}{% echo this that theother %}5678", {}, 'this that theother5678'),

    # {% load %} tag (within a child template)
    'inheritance19': ("{% extends 'inheritance01' %}{% block first %}{% load testtags %}{% echo 400 %}5678{% endblock %}", {}, '140056783_'),

    ### EXCEPTIONS ############################################################

    # Raise exception for invalid template name
    'exception01': ("{% extends 'nonexistent' %}", {}, template.TemplateSyntaxError),

    # Raise exception for invalid template name (in variable)
    'exception02': ("{% extends nonexistent %}", {}, template.TemplateSyntaxError),

    # Raise exception for extra {% extends %} tags
    'exception03': ("{% extends 'inheritance01' %}{% block first %}2{% endblock %}{% extends 'inheritance16' %}", {}, template.TemplateSyntaxError),

    # Raise exception for custom tags used in child with {% load %} tag in parent, not in child
    'exception04': ("{% extends 'inheritance17' %}{% block first %}{% echo 400 %}5678{% endblock %}", {}, template.TemplateSyntaxError),
}

# This replaces the standard template_loader.
def test_template_loader(template_name, template_dirs=None):
    try:
        return TEMPLATE_TESTS[template_name][0]
    except KeyError:
        raise template.TemplateDoesNotExist, template_name

def run_tests(verbosity=0, standalone=False):
    template_loader.load_template_source, old_template_loader = test_template_loader, template_loader.load_template_source
    failed_tests = []
    tests = TEMPLATE_TESTS.items()
    tests.sort()
    for name, vals in tests:
        try:
            output = template_loader.get_template(name).render(template.Context(vals[1]))
        except Exception, e:
            if e.__class__ == vals[2]:
                if verbosity:
                    print "Template test: %s -- Passed" % name
            else:
                if verbosity:
                    print "Template test: %s -- FAILED. Got %s, exception: %s" % (name, e.__class__, e)
                failed_tests.append(name)
            continue
        if output == vals[2]:
            if verbosity:
                print "Template test: %s -- Passed" % name
        else:
            if verbosity:
                print "Template test: %s -- FAILED. Expected %r, got %r" % (name, vals[2], output)
            failed_tests.append(name)
    template_loader.load_template_source = old_template_loader

    if failed_tests and not standalone:
        msg = "Template tests %s failed." % failed_tests
        if not verbosity:
            msg += "  Re-run tests with -v1 to see actual failures"
        raise Exception, msg

if __name__ == "__main__":
    run_tests(1, True)
