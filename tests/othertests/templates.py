from django.conf import settings


from django import template
from django.template import loader
from django.utils.translation import activate, deactivate, install
from datetime import datetime
import traceback

#################################
# Custom template tag for tests #
#################################

register = template.Library()

class EchoNode(template.Node):
    def __init__(self, contents):
        self.contents = contents

    def render(self, context):
        return " ".join(self.contents)

def do_echo(parser, token):
    return EchoNode(token.contents.split()[1:])

register.tag("echo", do_echo)

template.libraries['django.templatetags.testtags'] = register

#####################################
# Helper objects for template tests #
#####################################

class SomeException(Exception):
    silent_variable_failure = True

class SomeOtherException(Exception):
    pass

class SomeClass:
    def __init__(self):
        self.otherclass = OtherClass()

    def method(self):
        return "SomeClass.method"

    def method2(self, o):
        return o

    def method3(self):
        raise SomeException

    def method4(self):
        raise SomeOtherException

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

    # Escaped string as argument
    'basic-syntax30': (r'{{ var|default_if_none:" endquote\" hah" }}', {"var": None}, ' endquote" hah'),

    # Variable as argument
    'basic-syntax31': (r'{{ var|default_if_none:var2 }}', {"var": None, "var2": "happy"}, 'happy'),

    # Default argument testing
    'basic-syntax32': (r'{{ var|yesno:"yup,nup,mup" }} {{ var|yesno }}', {"var": True}, 'yup yes'),

    # Fail silently for methods that raise an exception with a "silent_variable_failure" attribute
    'basic-syntax33': (r'1{{ var.method3 }}2', {"var": SomeClass()}, "12"),

    # In methods that raise an exception without a "silent_variable_attribute" set to True,
    # the exception propogates
    'basic-syntax34': (r'1{{ var.method4 }}2', {"var": SomeClass()}, SomeOtherException),

    # Escaped backslash in argument
    'basic-syntax35': (r'{{ var|default_if_none:"foo\bar" }}', {"var": None}, r'foo\bar'),

    # Escaped backslash using known escape char
    'basic-syntax35': (r'{{ var|default_if_none:"foo\now" }}', {"var": None}, r'foo\now'),

    ### COMMENT TAG ###########################################################
    'comment-tag01': ("{% comment %}this is hidden{% endcomment %}hello", {}, "hello"),
    'comment-tag02': ("{% comment %}this is hidden{% endcomment %}hello{% comment %}foo{% endcomment %}", {}, "hello"),

    # Comment tag can contain invalid stuff.
    'comment-tag03': ("foo{% comment %} {% if %} {% endcomment %}", {}, "foo"),
    'comment-tag04': ("foo{% comment %} {% endblock %} {% endcomment %}", {}, "foo"),
    'comment-tag05': ("foo{% comment %} {% somerandomtag %} {% endcomment %}", {}, "foo"),

    ### CYCLE TAG #############################################################
    'cycle01': ('{% cycle a %}', {}, template.TemplateSyntaxError),
    'cycle02': ('{% cycle a,b,c as abc %}{% cycle abc %}', {}, 'ab'),
    'cycle03': ('{% cycle a,b,c as abc %}{% cycle abc %}{% cycle abc %}', {}, 'abc'),
    'cycle04': ('{% cycle a,b,c as abc %}{% cycle abc %}{% cycle abc %}{% cycle abc %}', {}, 'abca'),
    'cycle05': ('{% cycle %}', {}, template.TemplateSyntaxError),
    'cycle06': ('{% cycle a %}', {}, template.TemplateSyntaxError),
    'cycle07': ('{% cycle a,b,c as foo %}{% cycle bar %}', {}, template.TemplateSyntaxError),

    ### EXCEPTIONS ############################################################

    # Raise exception for invalid template name
    'exception01': ("{% extends 'nonexistent' %}", {}, template.TemplateSyntaxError),

    # Raise exception for invalid template name (in variable)
    'exception02': ("{% extends nonexistent %}", {}, template.TemplateSyntaxError),

    # Raise exception for extra {% extends %} tags
    'exception03': ("{% extends 'inheritance01' %}{% block first %}2{% endblock %}{% extends 'inheritance16' %}", {}, template.TemplateSyntaxError),

    # Raise exception for custom tags used in child with {% load %} tag in parent, not in child
    'exception04': ("{% extends 'inheritance17' %}{% block first %}{% echo 400 %}5678{% endblock %}", {}, template.TemplateSyntaxError),

    ### FILTER TAG ############################################################
    'filter01': ('{% filter upper %}{% endfilter %}', {}, ''),
    'filter02': ('{% filter upper %}django{% endfilter %}', {}, 'DJANGO'),
    'filter03': ('{% filter upper|lower %}django{% endfilter %}', {}, 'django'),

    ### FIRSTOF TAG ###########################################################
    'firstof01': ('{% firstof a b c %}', {'a':0,'b':0,'c':0}, ''),
    'firstof02': ('{% firstof a b c %}', {'a':1,'b':0,'c':0}, '1'),
    'firstof03': ('{% firstof a b c %}', {'a':0,'b':2,'c':0}, '2'),
    'firstof04': ('{% firstof a b c %}', {'a':0,'b':0,'c':3}, '3'),
    'firstof05': ('{% firstof a b c %}', {'a':1,'b':2,'c':3}, '1'),
    'firstof06': ('{% firstof %}', {}, template.TemplateSyntaxError),

    ### FOR TAG ###############################################################
    'for-tag01': ("{% for val in values %}{{ val }}{% endfor %}", {"values": [1, 2, 3]}, "123"),
    'for-tag02': ("{% for val in values reversed %}{{ val }}{% endfor %}", {"values": [1, 2, 3]}, "321"),
    'for-tag-vars01': ("{% for val in values %}{{ forloop.counter }}{% endfor %}", {"values": [6, 6, 6]}, "123"),
    'for-tag-vars02': ("{% for val in values %}{{ forloop.counter0 }}{% endfor %}", {"values": [6, 6, 6]}, "012"),
    'for-tag-vars03': ("{% for val in values %}{{ forloop.revcounter }}{% endfor %}", {"values": [6, 6, 6]}, "321"),
    'for-tag-vars04': ("{% for val in values %}{{ forloop.revcounter0 }}{% endfor %}", {"values": [6, 6, 6]}, "210"),

    ### IF TAG ################################################################
    'if-tag01': ("{% if foo %}yes{% else %}no{% endif %}", {"foo": True}, "yes"),
    'if-tag02': ("{% if foo %}yes{% else %}no{% endif %}", {"foo": False}, "no"),
    'if-tag03': ("{% if foo %}yes{% else %}no{% endif %}", {}, "no"),

    # AND
    'if-tag-and01': ("{% if foo and bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': True}, 'yes'),
    'if-tag-and02': ("{% if foo and bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': False}, 'no'),
    'if-tag-and03': ("{% if foo and bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': True}, 'no'),
    'if-tag-and04': ("{% if foo and bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': False}, 'no'),
    'if-tag-and05': ("{% if foo and bar %}yes{% else %}no{% endif %}", {'foo': False}, 'no'),
    'if-tag-and06': ("{% if foo and bar %}yes{% else %}no{% endif %}", {'bar': False}, 'no'),
    'if-tag-and07': ("{% if foo and bar %}yes{% else %}no{% endif %}", {'foo': True}, 'no'),
    'if-tag-and08': ("{% if foo and bar %}yes{% else %}no{% endif %}", {'bar': True}, 'no'),

    # OR
    'if-tag-or01': ("{% if foo or bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': True}, 'yes'),
    'if-tag-or02': ("{% if foo or bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': False}, 'yes'),
    'if-tag-or03': ("{% if foo or bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': True}, 'yes'),
    'if-tag-or04': ("{% if foo or bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': False}, 'no'),
    'if-tag-or05': ("{% if foo or bar %}yes{% else %}no{% endif %}", {'foo': False}, 'no'),
    'if-tag-or06': ("{% if foo or bar %}yes{% else %}no{% endif %}", {'bar': False}, 'no'),
    'if-tag-or07': ("{% if foo or bar %}yes{% else %}no{% endif %}", {'foo': True}, 'yes'),
    'if-tag-or08': ("{% if foo or bar %}yes{% else %}no{% endif %}", {'bar': True}, 'yes'),

    # TODO: multiple ORs

    # NOT
    'if-tag-not01': ("{% if not foo %}no{% else %}yes{% endif %}", {'foo': True}, 'yes'),
    'if-tag-not02': ("{% if not %}yes{% else %}no{% endif %}", {'foo': True}, 'no'),
    'if-tag-not03': ("{% if not %}yes{% else %}no{% endif %}", {'not': True}, 'yes'),
    'if-tag-not04': ("{% if not not %}no{% else %}yes{% endif %}", {'not': True}, 'yes'),
    'if-tag-not05': ("{% if not not %}no{% else %}yes{% endif %}", {}, 'no'),

    'if-tag-not06': ("{% if foo and not bar %}yes{% else %}no{% endif %}", {}, 'no'),
    'if-tag-not07': ("{% if foo and not bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': True}, 'no'),
    'if-tag-not08': ("{% if foo and not bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': False}, 'yes'),
    'if-tag-not09': ("{% if foo and not bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': True}, 'no'),
    'if-tag-not10': ("{% if foo and not bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': False}, 'no'),

    'if-tag-not11': ("{% if not foo and bar %}yes{% else %}no{% endif %}", {}, 'no'),
    'if-tag-not12': ("{% if not foo and bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': True}, 'no'),
    'if-tag-not13': ("{% if not foo and bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': False}, 'no'),
    'if-tag-not14': ("{% if not foo and bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': True}, 'yes'),
    'if-tag-not15': ("{% if not foo and bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': False}, 'no'),

    'if-tag-not16': ("{% if foo or not bar %}yes{% else %}no{% endif %}", {}, 'yes'),
    'if-tag-not17': ("{% if foo or not bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': True}, 'yes'),
    'if-tag-not18': ("{% if foo or not bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': False}, 'yes'),
    'if-tag-not19': ("{% if foo or not bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': True}, 'no'),
    'if-tag-not20': ("{% if foo or not bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': False}, 'yes'),

    'if-tag-not21': ("{% if not foo or bar %}yes{% else %}no{% endif %}", {}, 'yes'),
    'if-tag-not22': ("{% if not foo or bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': True}, 'yes'),
    'if-tag-not23': ("{% if not foo or bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': False}, 'no'),
    'if-tag-not24': ("{% if not foo or bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': True}, 'yes'),
    'if-tag-not25': ("{% if not foo or bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': False}, 'yes'),

    'if-tag-not26': ("{% if not foo and not bar %}yes{% else %}no{% endif %}", {}, 'yes'),
    'if-tag-not27': ("{% if not foo and not bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': True}, 'no'),
    'if-tag-not28': ("{% if not foo and not bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': False}, 'no'),
    'if-tag-not29': ("{% if not foo and not bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': True}, 'no'),
    'if-tag-not30': ("{% if not foo and not bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': False}, 'yes'),

    'if-tag-not31': ("{% if not foo or not bar %}yes{% else %}no{% endif %}", {}, 'yes'),
    'if-tag-not32': ("{% if not foo or not bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': True}, 'no'),
    'if-tag-not33': ("{% if not foo or not bar %}yes{% else %}no{% endif %}", {'foo': True, 'bar': False}, 'yes'),
    'if-tag-not34': ("{% if not foo or not bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': True}, 'yes'),
    'if-tag-not35': ("{% if not foo or not bar %}yes{% else %}no{% endif %}", {'foo': False, 'bar': False}, 'yes'),

    # AND and OR raises a TemplateSyntaxError
    'if-tag-error01': ("{% if foo or bar and baz %}yes{% else %}no{% endif %}", {'foo': False, 'bar': False}, template.TemplateSyntaxError),
    'if-tag-error02': ("{% if foo and %}yes{% else %}no{% endif %}", {'foo': True}, template.TemplateSyntaxError),
    'if-tag-error03': ("{% if foo or %}yes{% else %}no{% endif %}", {'foo': True}, template.TemplateSyntaxError),
    'if-tag-error04': ("{% if not foo and %}yes{% else %}no{% endif %}", {'foo': True}, template.TemplateSyntaxError),
    'if-tag-error05': ("{% if not foo or %}yes{% else %}no{% endif %}", {'foo': True}, template.TemplateSyntaxError),

    ### IFCHANGED TAG #########################################################
    'ifchanged01': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% endfor %}', { 'num': (1,2,3) }, '123'),
    'ifchanged02': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% endfor %}', { 'num': (1,1,3) }, '13'),
    'ifchanged03': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% endfor %}', { 'num': (1,1,1) }, '1'),

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

    # SMART SPLITTING
    'ifequal-split01': ('{% ifequal a "test man" %}yes{% else %}no{% endifequal %}', {}, "no"),
    'ifequal-split02': ('{% ifequal a "test man" %}yes{% else %}no{% endifequal %}', {'a': 'foo'}, "no"),
    'ifequal-split03': ('{% ifequal a "test man" %}yes{% else %}no{% endifequal %}', {'a': 'test man'}, "yes"),
    'ifequal-split04': ("{% ifequal a 'test man' %}yes{% else %}no{% endifequal %}", {'a': 'test man'}, "yes"),
    'ifequal-split05': ("{% ifequal a 'i \"love\" you' %}yes{% else %}no{% endifequal %}", {'a': ''}, "no"),
    'ifequal-split06': ("{% ifequal a 'i \"love\" you' %}yes{% else %}no{% endifequal %}", {'a': 'i "love" you'}, "yes"),
    'ifequal-split07': ("{% ifequal a 'i \"love\" you' %}yes{% else %}no{% endifequal %}", {'a': 'i love you'}, "no"),
    'ifequal-split08': (r"{% ifequal a 'I\'m happy' %}yes{% else %}no{% endifequal %}", {'a': "I'm happy"}, "yes"),
    'ifequal-split09': (r"{% ifequal a 'slash\man' %}yes{% else %}no{% endifequal %}", {'a': r"slash\man"}, "yes"),
    'ifequal-split10': (r"{% ifequal a 'slash\man' %}yes{% else %}no{% endifequal %}", {'a': r"slashman"}, "no"),

    ### IFNOTEQUAL TAG ########################################################
    'ifnotequal01': ("{% ifnotequal a b %}yes{% endifnotequal %}", {"a": 1, "b": 2}, "yes"),
    'ifnotequal02': ("{% ifnotequal a b %}yes{% endifnotequal %}", {"a": 1, "b": 1}, ""),
    'ifnotequal03': ("{% ifnotequal a b %}yes{% else %}no{% endifnotequal %}", {"a": 1, "b": 2}, "yes"),
    'ifnotequal04': ("{% ifnotequal a b %}yes{% else %}no{% endifnotequal %}", {"a": 1, "b": 1}, "no"),

    ### INCLUDE TAG ###########################################################
    'include01': ('{% include "basic-syntax01" %}', {}, "something cool"),
    'include02': ('{% include "basic-syntax02" %}', {'headline': 'Included'}, "Included"),
    'include03': ('{% include template_name %}', {'template_name': 'basic-syntax02', 'headline': 'Included'}, "Included"),
    'include04': ('a{% include "nonexistent" %}b', {}, "ab"),

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

    # Two-level inheritance with {{ block.super }}
    'inheritance20': ("{% extends 'inheritance01' %}{% block first %}{{ block.super }}a{% endblock %}", {}, '1_a3_'),

    # Three-level inheritance with {{ block.super }} from parent
    'inheritance21': ("{% extends 'inheritance02' %}{% block first %}{{ block.super }}a{% endblock %}", {}, '12a34'),

    # Three-level inheritance with {{ block.super }} from grandparent
    'inheritance22': ("{% extends 'inheritance04' %}{% block first %}{{ block.super }}a{% endblock %}", {}, '1_a3_'),

    # Three-level inheritance with {{ block.super }} from parent and grandparent
    'inheritance23': ("{% extends 'inheritance20' %}{% block first %}{{ block.super }}b{% endblock %}", {}, '1_ab3_'),

    ### I18N ##################################################################

    # {% spaceless %} tag
    'spaceless01': ("{% spaceless %} <b>    <i> text </i>    </b> {% endspaceless %}", {}, "<b> <i> text </i> </b>"),
    'spaceless02': ("{% spaceless %} <b> \n <i> text </i> \n </b> {% endspaceless %}", {}, "<b> <i> text </i> </b>"),
    'spaceless03': ("{% spaceless %}<b><i>text</i></b>{% endspaceless %}", {}, "<b><i>text</i></b>"),

    # simple translation of a string delimited by '
    'i18n01': ("{% load i18n %}{% trans 'xxxyyyxxx' %}", {}, "xxxyyyxxx"),

    # simple translation of a string delimited by "
    'i18n02': ('{% load i18n %}{% trans "xxxyyyxxx" %}', {}, "xxxyyyxxx"),

    # simple translation of a variable
    'i18n03': ('{% load i18n %}{% blocktrans %}{{ anton }}{% endblocktrans %}', {'anton': 'xxxyyyxxx'}, "xxxyyyxxx"),

    # simple translation of a variable and filter
    'i18n04': ('{% load i18n %}{% blocktrans with anton|lower as berta %}{{ berta }}{% endblocktrans %}', {'anton': 'XXXYYYXXX'}, "xxxyyyxxx"),

    # simple translation of a string with interpolation
    'i18n05': ('{% load i18n %}{% blocktrans %}xxx{{ anton }}xxx{% endblocktrans %}', {'anton': 'yyy'}, "xxxyyyxxx"),

    # simple translation of a string to german
    'i18n06': ('{% load i18n %}{% trans "Page not found" %}', {'LANGUAGE_CODE': 'de'}, "Seite nicht gefunden"),

    # translation of singular form
    'i18n07': ('{% load i18n %}{% blocktrans count number as counter %}singular{% plural %}plural{% endblocktrans %}', {'number': 1}, "singular"),

    # translation of plural form
    'i18n08': ('{% load i18n %}{% blocktrans count number as counter %}singular{% plural %}plural{% endblocktrans %}', {'number': 2}, "plural"),

    # simple non-translation (only marking) of a string to german
    'i18n09': ('{% load i18n %}{% trans "Page not found" noop %}', {'LANGUAGE_CODE': 'de'}, "Page not found"),

    # translation of a variable with a translated filter
    'i18n10': ('{{ bool|yesno:_("ja,nein") }}', {'bool': True}, 'ja'),

    # translation of a variable with a non-translated filter
    'i18n11': ('{{ bool|yesno:"ja,nein" }}', {'bool': True}, 'ja'),

    # usage of the get_available_languages tag
    'i18n12': ('{% load i18n %}{% get_available_languages as langs %}{% for lang in langs %}{% ifequal lang.0 "de" %}{{ lang.0 }}{% endifequal %}{% endfor %}', {}, 'de'),

    # translation of a constant string
    'i18n13': ('{{ _("Page not found") }}', {'LANGUAGE_CODE': 'de'}, 'Seite nicht gefunden'),

    ### MULTILINE #############################################################

    'multiline01': ("""
                    Hello,
                    boys.
                    How
                    are
                    you
                    gentlemen.
                    """,
                    {},
                    """
                    Hello,
                    boys.
                    How
                    are
                    you
                    gentlemen.
                    """),

    ### REGROUP TAG ###########################################################
    'regroup01': ('{% regroup data by bar as grouped %}' + \
                  '{% for group in grouped %}' + \
                  '{{ group.grouper }}:' + \
                  '{% for item in group.list %}' + \
                  '{{ item.foo }}' + \
                  '{% endfor %},' + \
                  '{% endfor %}',
                  {'data': [ {'foo':'c', 'bar':1},
                             {'foo':'d', 'bar':1},
                             {'foo':'a', 'bar':2},
                             {'foo':'b', 'bar':2},
                             {'foo':'x', 'bar':3}  ]},
                  '1:cd,2:ab,3:x,'),

    # Test for silent failure when target variable isn't found
    'regroup02': ('{% regroup data by bar as grouped %}' + \
                  '{% for group in grouped %}' + \
                  '{{ group.grouper }}:' + \
                  '{% for item in group.list %}' + \
                  '{{ item.foo }}' + \
                  '{% endfor %},' + \
                  '{% endfor %}',
                  {}, ''),

    ### TEMPLATETAG TAG #######################################################
    'templatetag01': ('{% templatetag openblock %}', {}, '{%'),
    'templatetag02': ('{% templatetag closeblock %}', {}, '%}'),
    'templatetag03': ('{% templatetag openvariable %}', {}, '{{'),
    'templatetag04': ('{% templatetag closevariable %}', {}, '}}'),
    'templatetag05': ('{% templatetag %}', {}, template.TemplateSyntaxError),
    'templatetag06': ('{% templatetag foo %}', {}, template.TemplateSyntaxError),

    ### WIDTHRATIO TAG ########################################################
    'widthratio01': ('{% widthratio a b 0 %}', {'a':50,'b':100}, '0'),
    'widthratio02': ('{% widthratio a b 100 %}', {'a':0,'b':0}, ''),
    'widthratio03': ('{% widthratio a b 100 %}', {'a':0,'b':100}, '0'),
    'widthratio04': ('{% widthratio a b 100 %}', {'a':50,'b':100}, '50'),
    'widthratio05': ('{% widthratio a b 100 %}', {'a':100,'b':100}, '100'),

    # 62.5 should round to 63
    'widthratio06': ('{% widthratio a b 100 %}', {'a':50,'b':80}, '63'),

    # 71.4 should round to 71
    'widthratio07': ('{% widthratio a b 100 %}', {'a':50,'b':70}, '71'),

    # Raise exception if we don't have 3 args, last one an integer
    'widthratio08': ('{% widthratio %}', {}, template.TemplateSyntaxError),
    'widthratio09': ('{% widthratio a b %}', {'a':50,'b':100}, template.TemplateSyntaxError),
    'widthratio10': ('{% widthratio a b 100.0 %}', {'a':50,'b':100}, template.TemplateSyntaxError),

    ### NOW TAG ########################################################
    # Simple case
    'now01' : ('{% now "j n Y"%}', {}, str(datetime.now().day) + ' ' + str(datetime.now().month) + ' ' + str(datetime.now().year)),

    # Check parsing of escaped and special characters
    'now02' : ('{% now "j "n" Y"%}', {}, template.TemplateSyntaxError),
#    'now03' : ('{% now "j \"n\" Y"%}', {}, str(datetime.now().day) + '"' + str(datetime.now().month) + '"' + str(datetime.now().year)),
#    'now04' : ('{% now "j \nn\n Y"%}', {}, str(datetime.now().day) + '\n' + str(datetime.now().month) + '\n' + str(datetime.now().year))
}

def test_template_loader(template_name, template_dirs=None):
    "A custom template loader that loads the unit-test templates."
    try:
        return (TEMPLATE_TESTS[template_name][0] , "test:%s" % template_name)
    except KeyError:
        raise template.TemplateDoesNotExist, template_name

def run_tests(verbosity=0, standalone=False):
    # Register our custom template loader.
    old_template_loaders = loader.template_source_loaders
    loader.template_source_loaders = [test_template_loader]

    failed_tests = []
    tests = TEMPLATE_TESTS.items()
    tests.sort()

    # Turn TEMPLATE_DEBUG off, because tests assume that.
    old_td, settings.TEMPLATE_DEBUG = settings.TEMPLATE_DEBUG, False
    for name, vals in tests:
        install()
        if 'LANGUAGE_CODE' in vals[1]:
            activate(vals[1]['LANGUAGE_CODE'])
        else:
            activate('en-us')
        try:
            output = loader.get_template(name).render(template.Context(vals[1]))
        except Exception, e:
            if e.__class__ == vals[2]:
                if verbosity:
                    print "Template test: %s -- Passed" % name
            else:
                if verbosity:
                    traceback.print_exc()
                    print "Template test: %s -- FAILED. Got %s, exception: %s" % (name, e.__class__, e)
                failed_tests.append(name)
            continue
        if 'LANGUAGE_CODE' in vals[1]:
            deactivate()
        if output == vals[2]:
            if verbosity:
                print "Template test: %s -- Passed" % name
        else:
            if verbosity:
                print "Template test: %s -- FAILED. Expected %r, got %r" % (name, vals[2], output)
            failed_tests.append(name)
    loader.template_source_loaders = old_template_loaders
    deactivate()
    settings.TEMPLATE_DEBUG = old_td

    if failed_tests and not standalone:
        msg = "Template tests %s failed." % failed_tests
        if not verbosity:
            msg += "  Re-run tests with -v1 to see actual failures"
        raise Exception, msg

if __name__ == "__main__":
    settings.configure()
    run_tests(1, True)
