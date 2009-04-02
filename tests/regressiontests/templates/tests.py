# -*- coding: utf-8 -*-
from django.conf import settings

if __name__ == '__main__':
    # When running this file in isolation, we need to set up the configuration
    # before importing 'template'.
    settings.configure()

from datetime import datetime, timedelta
import os
import sys
import traceback
import unittest

from django import template
from django.core import urlresolvers
from django.template import loader
from django.template.loaders import app_directories, filesystem
from django.utils.translation import activate, deactivate, ugettext as _
from django.utils.safestring import mark_safe
from django.utils.tzinfo import LocalTimezone

from context import context_tests
from custom import custom_filters
from parser import filter_parsing, variable_parsing
from unicode import unicode_tests

try:
    from loaders import *
except ImportError:
    pass # If setuptools isn't installed, that's fine. Just move on.

import filters

# Some other tests we would like to run
__test__ = {
    'unicode': unicode_tests,
    'context': context_tests,
    'filter_parsing': filter_parsing,
    'custom_filters': custom_filters,
}

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

class UTF8Class:
    "Class whose __str__ returns non-ASCII data"
    def __str__(self):
        return u'ŠĐĆŽćžšđ'.encode('utf-8')

class Templates(unittest.TestCase):
    def test_loaders_security(self):
        def test_template_sources(path, template_dirs, expected_sources):
            if isinstance(expected_sources, list):
                # Fix expected sources so they are normcased and abspathed
                expected_sources = [os.path.normcase(os.path.abspath(s)) for s in expected_sources]
            # Test the two loaders (app_directores and filesystem).
            func1 = lambda p, t: list(app_directories.get_template_sources(p, t))
            func2 = lambda p, t: list(filesystem.get_template_sources(p, t))
            for func in (func1, func2):
                if isinstance(expected_sources, list):
                    self.assertEqual(func(path, template_dirs), expected_sources)
                else:
                    self.assertRaises(expected_sources, func, path, template_dirs)

        template_dirs = ['/dir1', '/dir2']
        test_template_sources('index.html', template_dirs,
                              ['/dir1/index.html', '/dir2/index.html'])
        test_template_sources('/etc/passwd', template_dirs, [])
        test_template_sources('etc/passwd', template_dirs,
                              ['/dir1/etc/passwd', '/dir2/etc/passwd'])
        test_template_sources('../etc/passwd', template_dirs, [])
        test_template_sources('../../../etc/passwd', template_dirs, [])
        test_template_sources('/dir1/index.html', template_dirs,
                              ['/dir1/index.html'])
        test_template_sources('../dir2/index.html', template_dirs,
                              ['/dir2/index.html'])
        test_template_sources('/dir1blah', template_dirs, [])
        test_template_sources('../dir1blah', template_dirs, [])

        # UTF-8 bytestrings are permitted.
        test_template_sources('\xc3\x85ngstr\xc3\xb6m', template_dirs,
                              [u'/dir1/Ångström', u'/dir2/Ångström'])
        # Unicode strings are permitted.
        test_template_sources(u'Ångström', template_dirs,
                              [u'/dir1/Ångström', u'/dir2/Ångström'])
        test_template_sources(u'Ångström', ['/Straße'], [u'/Straße/Ångström'])
        test_template_sources('\xc3\x85ngstr\xc3\xb6m', ['/Straße'],
                              [u'/Straße/Ångström'])
        # Invalid UTF-8 encoding in bytestrings is not. Should raise a
        # semi-useful error message.
        test_template_sources('\xc3\xc3', template_dirs, UnicodeDecodeError)

        # Case insensitive tests (for win32). Not run unless we're on
        # a case insensitive operating system.
        if os.path.normcase('/TEST') == os.path.normpath('/test'):
            template_dirs = ['/dir1', '/DIR2']
            test_template_sources('index.html', template_dirs,
                                  ['/dir1/index.html', '/dir2/index.html'])
            test_template_sources('/DIR1/index.HTML', template_dirs,
                                  ['/dir1/index.html'])

    def test_token_smart_split(self):
        # Regression test for #7027
        token = template.Token(template.TOKEN_BLOCK, 'sometag _("Page not found") value|yesno:_("yes,no")')
        split = token.split_contents()
        self.assertEqual(split, ["sometag", '_("Page not found")', 'value|yesno:_("yes,no")'])

    def test_url_reverse_no_settings_module(self):
        #Regression test for #9005
        from django.template import Template, Context, TemplateSyntaxError
        
        old_settings_module = settings.SETTINGS_MODULE
        old_template_debug = settings.TEMPLATE_DEBUG
        
        settings.SETTINGS_MODULE = None
        settings.TEMPLATE_DEBUG = True
        
        t = Template('{% url will_not_match %}')
        c = Context()
        try:
            rendered = t.render(c)
        except TemplateSyntaxError, e:
            #Assert that we are getting the template syntax error and not the
            #string encoding error.
            self.assertEquals(e.message, "Caught an exception while rendering: Reverse for 'will_not_match' with arguments '()' and keyword arguments '{}' not found.")
        
        settings.SETTINGS_MODULE = old_settings_module
        settings.TEMPLATE_DEBUG = old_template_debug

    def test_templates(self):
        template_tests = self.get_template_tests()
        filter_tests = filters.get_filter_tests()

        # Quickly check that we aren't accidentally using a name in both
        # template and filter tests.
        overlapping_names = [name for name in filter_tests if name in template_tests]
        assert not overlapping_names, 'Duplicate test name(s): %s' % ', '.join(overlapping_names)

        template_tests.update(filter_tests)

        # Register our custom template loader.
        def test_template_loader(template_name, template_dirs=None):
            "A custom template loader that loads the unit-test templates."
            try:
                return (template_tests[template_name][0] , "test:%s" % template_name)
            except KeyError:
                raise template.TemplateDoesNotExist, template_name

        old_template_loaders = loader.template_source_loaders
        loader.template_source_loaders = [test_template_loader]

        failures = []
        tests = template_tests.items()
        tests.sort()

        # Turn TEMPLATE_DEBUG off, because tests assume that.
        old_td, settings.TEMPLATE_DEBUG = settings.TEMPLATE_DEBUG, False

        # Set TEMPLATE_STRING_IF_INVALID to a known string.
        old_invalid = settings.TEMPLATE_STRING_IF_INVALID
        expected_invalid_str = 'INVALID'

        for name, vals in tests:
            if isinstance(vals[2], tuple):
                normal_string_result = vals[2][0]
                invalid_string_result = vals[2][1]
                if '%s' in invalid_string_result:
                    expected_invalid_str = 'INVALID %s'
                    invalid_string_result = invalid_string_result % vals[2][2]
                    template.invalid_var_format_string = True
            else:
                normal_string_result = vals[2]
                invalid_string_result = vals[2]

            if 'LANGUAGE_CODE' in vals[1]:
                activate(vals[1]['LANGUAGE_CODE'])
            else:
                activate('en-us')

            for invalid_str, result in [('', normal_string_result),
                                        (expected_invalid_str, invalid_string_result)]:
                settings.TEMPLATE_STRING_IF_INVALID = invalid_str
                try:
                    test_template = loader.get_template(name)
                    output = self.render(test_template, vals)
                except Exception:
                    exc_type, exc_value, exc_tb = sys.exc_info()
                    if exc_type != result:
                        tb = '\n'.join(traceback.format_exception(exc_type, exc_value, exc_tb))
                        failures.append("Template test (TEMPLATE_STRING_IF_INVALID='%s'): %s -- FAILED. Got %s, exception: %s\n%s" % (invalid_str, name, exc_type, exc_value, tb))
                    continue
                if output != result:
                    failures.append("Template test (TEMPLATE_STRING_IF_INVALID='%s'): %s -- FAILED. Expected %r, got %r" % (invalid_str, name, result, output))

            if 'LANGUAGE_CODE' in vals[1]:
                deactivate()

            if template.invalid_var_format_string:
                expected_invalid_str = 'INVALID'
                template.invalid_var_format_string = False

        loader.template_source_loaders = old_template_loaders
        deactivate()
        settings.TEMPLATE_DEBUG = old_td
        settings.TEMPLATE_STRING_IF_INVALID = old_invalid

        self.assertEqual(failures, [], "Tests failed:\n%s\n%s" %
            ('-'*70, ("\n%s\n" % ('-'*70)).join(failures)))

    def render(self, test_template, vals):
        return test_template.render(template.Context(vals[1]))

    def get_template_tests(self):
        # SYNTAX --
        # 'template_name': ('template contents', 'context dict', 'expected string output' or Exception class)
        return {
            ### BASIC SYNTAX ################################################

            # Plain text should go through the template parser untouched
            'basic-syntax01': ("something cool", {}, "something cool"),

            # Variables should be replaced with their value in the current
            # context
            'basic-syntax02': ("{{ headline }}", {'headline':'Success'}, "Success"),

            # More than one replacement variable is allowed in a template
            'basic-syntax03': ("{{ first }} --- {{ second }}", {"first" : 1, "second" : 2}, "1 --- 2"),

            # Fail silently when a variable is not found in the current context
            'basic-syntax04': ("as{{ missing }}df", {}, ("asdf","asINVALIDdf")),

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
            'basic-syntax11': ("{{ var.blech }}", {"var": SomeClass()}, ("","INVALID")),

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
            'basic-syntax19': ("{{ foo.spam }}", {"foo" : {"bar" : "baz"}}, ("","INVALID")),

            # Fail silently when accessing a non-simple method
            'basic-syntax20': ("{{ var.method2 }}", {"var": SomeClass()}, ("","INVALID")),

            # Don't get confused when parsing something that is almost, but not
            # quite, a template tag.
            'basic-syntax21': ("a {{ moo %} b", {}, "a {{ moo %} b"),
            'basic-syntax22': ("{{ moo #}", {}, "{{ moo #}"),

            # Will try to treat "moo #} {{ cow" as the variable. Not ideal, but
            # costly to work around, so this triggers an error.
            'basic-syntax23': ("{{ moo #} {{ cow }}", {"cow": "cow"}, template.TemplateSyntaxError),

            # Embedded newlines make it not-a-tag.
            'basic-syntax24': ("{{ moo\n }}", {}, "{{ moo\n }}"),

            # Literal strings are permitted inside variables, mostly for i18n
            # purposes.
            'basic-syntax25': ('{{ "fred" }}', {}, "fred"),
            'basic-syntax26': (r'{{ "\"fred\"" }}', {}, "\"fred\""),
            'basic-syntax27': (r'{{ _("\"fred\"") }}', {}, "\"fred\""),

            # List-index syntax allows a template to access a certain item of a subscriptable object.
            'list-index01': ("{{ var.1 }}", {"var": ["first item", "second item"]}, "second item"),

            # Fail silently when the list index is out of range.
            'list-index02': ("{{ var.5 }}", {"var": ["first item", "second item"]}, ("", "INVALID")),

            # Fail silently when the variable is not a subscriptable object.
            'list-index03': ("{{ var.1 }}", {"var": None}, ("", "INVALID")),

            # Fail silently when variable is a dict without the specified key.
            'list-index04': ("{{ var.1 }}", {"var": {}}, ("", "INVALID")),

            # Dictionary lookup wins out when dict's key is a string.
            'list-index05': ("{{ var.1 }}", {"var": {'1': "hello"}}, "hello"),

            # But list-index lookup wins out when dict's key is an int, which
            # behind the scenes is really a dictionary lookup (for a dict)
            # after converting the key to an int.
            'list-index06': ("{{ var.1 }}", {"var": {1: "hello"}}, "hello"),

            # Dictionary lookup wins out when there is a string and int version of the key.
            'list-index07': ("{{ var.1 }}", {"var": {'1': "hello", 1: "world"}}, "hello"),

            # Basic filter usage
            'filter-syntax01': ("{{ var|upper }}", {"var": "Django is the greatest!"}, "DJANGO IS THE GREATEST!"),

            # Chained filters
            'filter-syntax02': ("{{ var|upper|lower }}", {"var": "Django is the greatest!"}, "django is the greatest!"),

            # Raise TemplateSyntaxError for space between a variable and filter pipe
            'filter-syntax03': ("{{ var |upper }}", {}, template.TemplateSyntaxError),

            # Raise TemplateSyntaxError for space after a filter pipe
            'filter-syntax04': ("{{ var| upper }}", {}, template.TemplateSyntaxError),

            # Raise TemplateSyntaxError for a nonexistent filter
            'filter-syntax05': ("{{ var|does_not_exist }}", {}, template.TemplateSyntaxError),

            # Raise TemplateSyntaxError when trying to access a filter containing an illegal character
            'filter-syntax06': ("{{ var|fil(ter) }}", {}, template.TemplateSyntaxError),

            # Raise TemplateSyntaxError for invalid block tags
            'filter-syntax07': ("{% nothing_to_see_here %}", {}, template.TemplateSyntaxError),

            # Raise TemplateSyntaxError for empty block tags
            'filter-syntax08': ("{% %}", {}, template.TemplateSyntaxError),

            # Chained filters, with an argument to the first one
            'filter-syntax09': ('{{ var|removetags:"b i"|upper|lower }}', {"var": "<b><i>Yes</i></b>"}, "yes"),

            # Literal string as argument is always "safe" from auto-escaping..
            'filter-syntax10': (r'{{ var|default_if_none:" endquote\" hah" }}',
                    {"var": None}, ' endquote" hah'),

            # Variable as argument
            'filter-syntax11': (r'{{ var|default_if_none:var2 }}', {"var": None, "var2": "happy"}, 'happy'),

            # Default argument testing
            'filter-syntax12': (r'{{ var|yesno:"yup,nup,mup" }} {{ var|yesno }}', {"var": True}, 'yup yes'),

            # Fail silently for methods that raise an exception with a
            # "silent_variable_failure" attribute
            'filter-syntax13': (r'1{{ var.method3 }}2', {"var": SomeClass()}, ("12", "1INVALID2")),

            # In methods that raise an exception without a
            # "silent_variable_attribute" set to True, the exception propagates
            'filter-syntax14': (r'1{{ var.method4 }}2', {"var": SomeClass()}, SomeOtherException),

            # Escaped backslash in argument
            'filter-syntax15': (r'{{ var|default_if_none:"foo\bar" }}', {"var": None}, r'foo\bar'),

            # Escaped backslash using known escape char
            'filter-syntax16': (r'{{ var|default_if_none:"foo\now" }}', {"var": None}, r'foo\now'),

            # Empty strings can be passed as arguments to filters
            'filter-syntax17': (r'{{ var|join:"" }}', {'var': ['a', 'b', 'c']}, 'abc'),

            # Make sure that any unicode strings are converted to bytestrings
            # in the final output.
            'filter-syntax18': (r'{{ var }}', {'var': UTF8Class()}, u'\u0160\u0110\u0106\u017d\u0107\u017e\u0161\u0111'),

            # Numbers as filter arguments should work
            'filter-syntax19': ('{{ var|truncatewords:1 }}', {"var": "hello world"}, "hello ..."),

            #filters should accept empty string constants
            'filter-syntax20': ('{{ ""|default_if_none:"was none" }}', {}, ""),

            ### COMMENT SYNTAX ########################################################
            'comment-syntax01': ("{# this is hidden #}hello", {}, "hello"),
            'comment-syntax02': ("{# this is hidden #}hello{# foo #}", {}, "hello"),

            # Comments can contain invalid stuff.
            'comment-syntax03': ("foo{#  {% if %}  #}", {}, "foo"),
            'comment-syntax04': ("foo{#  {% endblock %}  #}", {}, "foo"),
            'comment-syntax05': ("foo{#  {% somerandomtag %}  #}", {}, "foo"),
            'comment-syntax06': ("foo{# {% #}", {}, "foo"),
            'comment-syntax07': ("foo{# %} #}", {}, "foo"),
            'comment-syntax08': ("foo{# %} #}bar", {}, "foobar"),
            'comment-syntax09': ("foo{# {{ #}", {}, "foo"),
            'comment-syntax10': ("foo{# }} #}", {}, "foo"),
            'comment-syntax11': ("foo{# { #}", {}, "foo"),
            'comment-syntax12': ("foo{# } #}", {}, "foo"),

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
            'cycle08': ('{% cycle a,b,c as foo %}{% cycle foo %}{{ foo }}{{ foo }}{% cycle foo %}{{ foo }}', {}, 'abbbcc'),
            'cycle09': ("{% for i in test %}{% cycle a,b %}{{ i }},{% endfor %}", {'test': range(5)}, 'a0,b1,a2,b3,a4,'),
            'cycle10': ("{% cycle 'a' 'b' 'c' as abc %}{% cycle abc %}", {}, 'ab'),
            'cycle11': ("{% cycle 'a' 'b' 'c' as abc %}{% cycle abc %}{% cycle abc %}", {}, 'abc'),
            'cycle12': ("{% cycle 'a' 'b' 'c' as abc %}{% cycle abc %}{% cycle abc %}{% cycle abc %}", {}, 'abca'),
            'cycle13': ("{% for i in test %}{% cycle 'a' 'b' %}{{ i }},{% endfor %}", {'test': range(5)}, 'a0,b1,a2,b3,a4,'),
            'cycle14': ("{% cycle one two as foo %}{% cycle foo %}", {'one': '1','two': '2'}, '12'),
            'cycle15': ("{% for i in test %}{% cycle aye bee %}{{ i }},{% endfor %}", {'test': range(5), 'aye': 'a', 'bee': 'b'}, 'a0,b1,a2,b3,a4,'),
            'cycle16': ("{% cycle one|lower two as foo %}{% cycle foo %}", {'one': 'A','two': '2'}, 'a2'),

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
            'filter04': ('{% filter cut:remove %}djangospam{% endfilter %}', {'remove': 'spam'}, 'django'),

            ### FIRSTOF TAG ###########################################################
            'firstof01': ('{% firstof a b c %}', {'a':0,'b':0,'c':0}, ''),
            'firstof02': ('{% firstof a b c %}', {'a':1,'b':0,'c':0}, '1'),
            'firstof03': ('{% firstof a b c %}', {'a':0,'b':2,'c':0}, '2'),
            'firstof04': ('{% firstof a b c %}', {'a':0,'b':0,'c':3}, '3'),
            'firstof05': ('{% firstof a b c %}', {'a':1,'b':2,'c':3}, '1'),
            'firstof06': ('{% firstof a b c %}', {'b':0,'c':3}, '3'),
            'firstof07': ('{% firstof a b "c" %}', {'a':0}, 'c'),
            'firstof08': ('{% firstof a b "c and d" %}', {'a':0,'b':0}, 'c and d'),
            'firstof09': ('{% firstof %}', {}, template.TemplateSyntaxError),

            ### FOR TAG ###############################################################
            'for-tag01': ("{% for val in values %}{{ val }}{% endfor %}", {"values": [1, 2, 3]}, "123"),
            'for-tag02': ("{% for val in values reversed %}{{ val }}{% endfor %}", {"values": [1, 2, 3]}, "321"),
            'for-tag-vars01': ("{% for val in values %}{{ forloop.counter }}{% endfor %}", {"values": [6, 6, 6]}, "123"),
            'for-tag-vars02': ("{% for val in values %}{{ forloop.counter0 }}{% endfor %}", {"values": [6, 6, 6]}, "012"),
            'for-tag-vars03': ("{% for val in values %}{{ forloop.revcounter }}{% endfor %}", {"values": [6, 6, 6]}, "321"),
            'for-tag-vars04': ("{% for val in values %}{{ forloop.revcounter0 }}{% endfor %}", {"values": [6, 6, 6]}, "210"),
            'for-tag-vars05': ("{% for val in values %}{% if forloop.first %}f{% else %}x{% endif %}{% endfor %}", {"values": [6, 6, 6]}, "fxx"),
            'for-tag-vars06': ("{% for val in values %}{% if forloop.last %}l{% else %}x{% endif %}{% endfor %}", {"values": [6, 6, 6]}, "xxl"),
            'for-tag-unpack01': ("{% for key,value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
            'for-tag-unpack03': ("{% for key, value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
            'for-tag-unpack04': ("{% for key , value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
            'for-tag-unpack05': ("{% for key ,value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
            'for-tag-unpack06': ("{% for key value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, template.TemplateSyntaxError),
            'for-tag-unpack07': ("{% for key,,value in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, template.TemplateSyntaxError),
            'for-tag-unpack08': ("{% for key,value, in items %}{{ key }}:{{ value }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, template.TemplateSyntaxError),
            # Ensure that a single loopvar doesn't truncate the list in val.
            'for-tag-unpack09': ("{% for val in items %}{{ val.0 }}:{{ val.1 }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, "one:1/two:2/"),
            # Otherwise, silently truncate if the length of loopvars differs to the length of each set of items.
            'for-tag-unpack10': ("{% for x,y in items %}{{ x }}:{{ y }}/{% endfor %}", {"items": (('one', 1, 'carrot'), ('two', 2, 'orange'))}, "one:1/two:2/"),
            'for-tag-unpack11': ("{% for x,y,z in items %}{{ x }}:{{ y }},{{ z }}/{% endfor %}", {"items": (('one', 1), ('two', 2))}, ("one:1,/two:2,/", "one:1,INVALID/two:2,INVALID/")),
            'for-tag-unpack12': ("{% for x,y,z in items %}{{ x }}:{{ y }},{{ z }}/{% endfor %}", {"items": (('one', 1, 'carrot'), ('two', 2))}, ("one:1,carrot/two:2,/", "one:1,carrot/two:2,INVALID/")),
            'for-tag-unpack13': ("{% for x,y,z in items %}{{ x }}:{{ y }},{{ z }}/{% endfor %}", {"items": (('one', 1, 'carrot'), ('two', 2, 'cheese'))}, ("one:1,carrot/two:2,cheese/", "one:1,carrot/two:2,cheese/")),
            'for-tag-empty01': ("{% for val in values %}{{ val }}{% empty %}empty text{% endfor %}", {"values": [1, 2, 3]}, "123"),
            'for-tag-empty02': ("{% for val in values %}{{ val }}{% empty %}values array empty{% endfor %}", {"values": []}, "values array empty"),
            'for-tag-empty03': ("{% for val in values %}{{ val }}{% empty %}values array not found{% endfor %}", {}, "values array not found"),

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
            'ifchanged01': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% endfor %}', {'num': (1,2,3)}, '123'),
            'ifchanged02': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% endfor %}', {'num': (1,1,3)}, '13'),
            'ifchanged03': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% endfor %}', {'num': (1,1,1)}, '1'),
            'ifchanged04': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% for x in numx %}{% ifchanged %}{{ x }}{% endifchanged %}{% endfor %}{% endfor %}', {'num': (1, 2, 3), 'numx': (2, 2, 2)}, '122232'),
            'ifchanged05': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% for x in numx %}{% ifchanged %}{{ x }}{% endifchanged %}{% endfor %}{% endfor %}', {'num': (1, 1, 1), 'numx': (1, 2, 3)}, '1123123123'),
            'ifchanged06': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% for x in numx %}{% ifchanged %}{{ x }}{% endifchanged %}{% endfor %}{% endfor %}', {'num': (1, 1, 1), 'numx': (2, 2, 2)}, '1222'),
            'ifchanged07': ('{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% for x in numx %}{% ifchanged %}{{ x }}{% endifchanged %}{% for y in numy %}{% ifchanged %}{{ y }}{% endifchanged %}{% endfor %}{% endfor %}{% endfor %}', {'num': (1, 1, 1), 'numx': (2, 2, 2), 'numy': (3, 3, 3)}, '1233323332333'),
            'ifchanged08': ('{% for data in datalist %}{% for c,d in data %}{% if c %}{% ifchanged %}{{ d }}{% endifchanged %}{% endif %}{% endfor %}{% endfor %}', {'datalist': [[(1, 'a'), (1, 'a'), (0, 'b'), (1, 'c')], [(0, 'a'), (1, 'c'), (1, 'd'), (1, 'd'), (0, 'e')]]}, 'accd'),

            # Test one parameter given to ifchanged.
            'ifchanged-param01': ('{% for n in num %}{% ifchanged n %}..{% endifchanged %}{{ n }}{% endfor %}', { 'num': (1,2,3) }, '..1..2..3'),
            'ifchanged-param02': ('{% for n in num %}{% for x in numx %}{% ifchanged n %}..{% endifchanged %}{{ x }}{% endfor %}{% endfor %}', { 'num': (1,2,3), 'numx': (5,6,7) }, '..567..567..567'),

            # Test multiple parameters to ifchanged.
            'ifchanged-param03': ('{% for n in num %}{{ n }}{% for x in numx %}{% ifchanged x n %}{{ x }}{% endifchanged %}{% endfor %}{% endfor %}', { 'num': (1,1,2), 'numx': (5,6,6) }, '156156256'),

            # Test a date+hour like construct, where the hour of the last day
            # is the same but the date had changed, so print the hour anyway.
            'ifchanged-param04': ('{% for d in days %}{% ifchanged %}{{ d.day }}{% endifchanged %}{% for h in d.hours %}{% ifchanged d h %}{{ h }}{% endifchanged %}{% endfor %}{% endfor %}', {'days':[{'day':1, 'hours':[1,2,3]},{'day':2, 'hours':[3]},] }, '112323'),

            # Logically the same as above, just written with explicit
            # ifchanged for the day.
            'ifchanged-param04': ('{% for d in days %}{% ifchanged d.day %}{{ d.day }}{% endifchanged %}{% for h in d.hours %}{% ifchanged d.day h %}{{ h }}{% endifchanged %}{% endfor %}{% endfor %}', {'days':[{'day':1, 'hours':[1,2,3]},{'day':2, 'hours':[3]},] }, '112323'),

            # Test the else clause of ifchanged.
            'ifchanged-else01': ('{% for id in ids %}{{ id }}{% ifchanged id %}-first{% else %}-other{% endifchanged %},{% endfor %}', {'ids': [1,1,2,2,2,3]}, '1-first,1-other,2-first,2-other,2-other,3-first,'),

            'ifchanged-else02': ('{% for id in ids %}{{ id }}-{% ifchanged id %}{% cycle red,blue %}{% else %}grey{% endifchanged %},{% endfor %}', {'ids': [1,1,2,2,2,3]}, '1-red,1-grey,2-blue,2-grey,2-grey,3-red,'),
            'ifchanged-else03': ('{% for id in ids %}{{ id }}{% ifchanged id %}-{% cycle red,blue %}{% else %}{% endifchanged %},{% endfor %}', {'ids': [1,1,2,2,2,3]}, '1-red,1,2-blue,2,2,3-red,'),

            'ifchanged-else04': ('{% for id in ids %}{% ifchanged %}***{{ id }}*{% else %}...{% endifchanged %}{{ forloop.counter }}{% endfor %}', {'ids': [1,1,2,2,2,3,4]}, '***1*1...2***2*3...4...5***3*6***4*7'),

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

            # NUMERIC RESOLUTION
            'ifequal-numeric01': ('{% ifequal x 5 %}yes{% endifequal %}', {'x': '5'}, ''),
            'ifequal-numeric02': ('{% ifequal x 5 %}yes{% endifequal %}', {'x': 5}, 'yes'),
            'ifequal-numeric03': ('{% ifequal x 5.2 %}yes{% endifequal %}', {'x': 5}, ''),
            'ifequal-numeric04': ('{% ifequal x 5.2 %}yes{% endifequal %}', {'x': 5.2}, 'yes'),
            'ifequal-numeric05': ('{% ifequal x 0.2 %}yes{% endifequal %}', {'x': .2}, 'yes'),
            'ifequal-numeric06': ('{% ifequal x .2 %}yes{% endifequal %}', {'x': .2}, 'yes'),
            'ifequal-numeric07': ('{% ifequal x 2. %}yes{% endifequal %}', {'x': 2}, ''),
            'ifequal-numeric08': ('{% ifequal x "5" %}yes{% endifequal %}', {'x': 5}, ''),
            'ifequal-numeric09': ('{% ifequal x "5" %}yes{% endifequal %}', {'x': '5'}, 'yes'),
            'ifequal-numeric10': ('{% ifequal x -5 %}yes{% endifequal %}', {'x': -5}, 'yes'),
            'ifequal-numeric11': ('{% ifequal x -5.2 %}yes{% endifequal %}', {'x': -5.2}, 'yes'),
            'ifequal-numeric12': ('{% ifequal x +5 %}yes{% endifequal %}', {'x': 5}, 'yes'),

            # FILTER EXPRESSIONS AS ARGUMENTS
            'ifequal-filter01': ('{% ifequal a|upper "A" %}x{% endifequal %}', {'a': 'a'}, 'x'),
            'ifequal-filter02': ('{% ifequal "A" a|upper %}x{% endifequal %}', {'a': 'a'}, 'x'),
            'ifequal-filter03': ('{% ifequal a|upper b|upper %}x{% endifequal %}', {'a': 'x', 'b': 'X'}, 'x'),
            'ifequal-filter04': ('{% ifequal x|slice:"1" "a" %}x{% endifequal %}', {'x': 'aaa'}, 'x'),
            'ifequal-filter05': ('{% ifequal x|slice:"1"|upper "A" %}x{% endifequal %}', {'x': 'aaa'}, 'x'),

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
            'include 05': ('template with a space', {}, 'template with a space'),
            'include06': ('{% include "include 05"%}', {}, 'template with a space'),

            ### NAMED ENDBLOCKS #######################################################

            # Basic test
            'namedendblocks01': ("1{% block first %}_{% block second %}2{% endblock second %}_{% endblock first %}3", {}, '1_2_3'),

            # Unbalanced blocks
            'namedendblocks02': ("1{% block first %}_{% block second %}2{% endblock first %}_{% endblock second %}3", {}, template.TemplateSyntaxError),
            'namedendblocks03': ("1{% block first %}_{% block second %}2{% endblock %}_{% endblock second %}3", {}, template.TemplateSyntaxError),
            'namedendblocks04': ("1{% block first %}_{% block second %}2{% endblock second %}_{% endblock third %}3", {}, template.TemplateSyntaxError),
            'namedendblocks05': ("1{% block first %}_{% block second %}2{% endblock first %}", {}, template.TemplateSyntaxError),

            # Mixed named and unnamed endblocks
            'namedendblocks06': ("1{% block first %}_{% block second %}2{% endblock %}_{% endblock first %}3", {}, '1_2_3'),
            'namedendblocks07': ("1{% block first %}_{% block second %}2{% endblock second %}_{% endblock %}3", {}, '1_2_3'),

            ### INHERITANCE ###########################################################

            # Standard template with no inheritance
            'inheritance01': ("1{% block first %}&{% endblock %}3{% block second %}_{% endblock %}", {}, '1&3_'),

            # Standard two-level inheritance
            'inheritance02': ("{% extends 'inheritance01' %}{% block first %}2{% endblock %}{% block second %}4{% endblock %}", {}, '1234'),

            # Three-level with no redefinitions on third level
            'inheritance03': ("{% extends 'inheritance02' %}", {}, '1234'),

            # Two-level with no redefinitions on second level
            'inheritance04': ("{% extends 'inheritance01' %}", {}, '1&3_'),

            # Two-level with double quotes instead of single quotes
            'inheritance05': ('{% extends "inheritance02" %}', {}, '1234'),

            # Three-level with variable parent-template name
            'inheritance06': ("{% extends foo %}", {'foo': 'inheritance02'}, '1234'),

            # Two-level with one block defined, one block not defined
            'inheritance07': ("{% extends 'inheritance01' %}{% block second %}5{% endblock %}", {}, '1&35'),

            # Three-level with one block defined on this level, two blocks defined next level
            'inheritance08': ("{% extends 'inheritance02' %}{% block second %}5{% endblock %}", {}, '1235'),

            # Three-level with second and third levels blank
            'inheritance09': ("{% extends 'inheritance04' %}", {}, '1&3_'),

            # Three-level with space NOT in a block -- should be ignored
            'inheritance10': ("{% extends 'inheritance04' %}      ", {}, '1&3_'),

            # Three-level with both blocks defined on this level, but none on second level
            'inheritance11': ("{% extends 'inheritance04' %}{% block first %}2{% endblock %}{% block second %}4{% endblock %}", {}, '1234'),

            # Three-level with this level providing one and second level providing the other
            'inheritance12': ("{% extends 'inheritance07' %}{% block first %}2{% endblock %}", {}, '1235'),

            # Three-level with this level overriding second level
            'inheritance13': ("{% extends 'inheritance02' %}{% block first %}a{% endblock %}{% block second %}b{% endblock %}", {}, '1a3b'),

            # A block defined only in a child template shouldn't be displayed
            'inheritance14': ("{% extends 'inheritance01' %}{% block newblock %}NO DISPLAY{% endblock %}", {}, '1&3_'),

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
            'inheritance20': ("{% extends 'inheritance01' %}{% block first %}{{ block.super }}a{% endblock %}", {}, '1&a3_'),

            # Three-level inheritance with {{ block.super }} from parent
            'inheritance21': ("{% extends 'inheritance02' %}{% block first %}{{ block.super }}a{% endblock %}", {}, '12a34'),

            # Three-level inheritance with {{ block.super }} from grandparent
            'inheritance22': ("{% extends 'inheritance04' %}{% block first %}{{ block.super }}a{% endblock %}", {}, '1&a3_'),

            # Three-level inheritance with {{ block.super }} from parent and grandparent
            'inheritance23': ("{% extends 'inheritance20' %}{% block first %}{{ block.super }}b{% endblock %}", {}, '1&ab3_'),

            # Inheritance from local context without use of template loader
            'inheritance24': ("{% extends context_template %}{% block first %}2{% endblock %}{% block second %}4{% endblock %}", {'context_template': template.Template("1{% block first %}_{% endblock %}3{% block second %}_{% endblock %}")}, '1234'),

            # Inheritance from local context with variable parent template
            'inheritance25': ("{% extends context_template.1 %}{% block first %}2{% endblock %}{% block second %}4{% endblock %}", {'context_template': [template.Template("Wrong"), template.Template("1{% block first %}_{% endblock %}3{% block second %}_{% endblock %}")]}, '1234'),

            # Set up a base template to extend
            'inheritance26': ("no tags", {}, 'no tags'),

            # Inheritance from a template that doesn't have any blocks
            'inheritance27': ("{% extends 'inheritance26' %}", {}, 'no tags'),

            # Set up a base template with a space in it.
            'inheritance 28': ("{% block first %}!{% endblock %}", {}, '!'),

            # Inheritance from a template with a space in its name should work.
            'inheritance29': ("{% extends 'inheritance 28' %}", {}, '!'),

            ### I18N ##################################################################

            # {% spaceless %} tag
            'spaceless01': ("{% spaceless %} <b>    <i> text </i>    </b> {% endspaceless %}", {}, "<b><i> text </i></b>"),
            'spaceless02': ("{% spaceless %} <b> \n <i> text </i> \n </b> {% endspaceless %}", {}, "<b><i> text </i></b>"),
            'spaceless03': ("{% spaceless %}<b><i>text</i></b>{% endspaceless %}", {}, "<b><i>text</i></b>"),

            # simple translation of a string delimited by '
            'i18n01': ("{% load i18n %}{% trans 'xxxyyyxxx' %}", {}, "xxxyyyxxx"),

            # simple translation of a string delimited by "
            'i18n02': ('{% load i18n %}{% trans "xxxyyyxxx" %}', {}, "xxxyyyxxx"),

            # simple translation of a variable
            'i18n03': ('{% load i18n %}{% blocktrans %}{{ anton }}{% endblocktrans %}', {'anton': '\xc3\x85'}, u"Å"),

            # simple translation of a variable and filter
            'i18n04': ('{% load i18n %}{% blocktrans with anton|lower as berta %}{{ berta }}{% endblocktrans %}', {'anton': '\xc3\x85'}, u'å'),

            # simple translation of a string with interpolation
            'i18n05': ('{% load i18n %}{% blocktrans %}xxx{{ anton }}xxx{% endblocktrans %}', {'anton': 'yyy'}, "xxxyyyxxx"),

            # simple translation of a string to german
            'i18n06': ('{% load i18n %}{% trans "Page not found" %}', {'LANGUAGE_CODE': 'de'}, "Seite nicht gefunden"),

            # translation of singular form
            'i18n07': ('{% load i18n %}{% blocktrans count number as counter %}singular{% plural %}{{ counter }} plural{% endblocktrans %}', {'number': 1}, "singular"),

            # translation of plural form
            'i18n08': ('{% load i18n %}{% blocktrans count number as counter %}singular{% plural %}{{ counter }} plural{% endblocktrans %}', {'number': 2}, "2 plural"),

            # simple non-translation (only marking) of a string to german
            'i18n09': ('{% load i18n %}{% trans "Page not found" noop %}', {'LANGUAGE_CODE': 'de'}, "Page not found"),

            # translation of a variable with a translated filter
            'i18n10': ('{{ bool|yesno:_("yes,no,maybe") }}', {'bool': True, 'LANGUAGE_CODE': 'de'}, 'Ja'),

            # translation of a variable with a non-translated filter
            'i18n11': ('{{ bool|yesno:"ja,nein" }}', {'bool': True}, 'ja'),

            # usage of the get_available_languages tag
            'i18n12': ('{% load i18n %}{% get_available_languages as langs %}{% for lang in langs %}{% ifequal lang.0 "de" %}{{ lang.0 }}{% endifequal %}{% endfor %}', {}, 'de'),

            # translation of constant strings
            'i18n13': ('{{ _("Password") }}', {'LANGUAGE_CODE': 'de'}, 'Passwort'),
            'i18n14': ('{% cycle "foo" _("Password") _(\'Password\') as c %} {% cycle c %} {% cycle c %}', {'LANGUAGE_CODE': 'de'}, 'foo Passwort Passwort'),
            'i18n15': ('{{ absent|default:_("Password") }}', {'LANGUAGE_CODE': 'de', 'absent': ""}, 'Passwort'),
            'i18n16': ('{{ _("<") }}', {'LANGUAGE_CODE': 'de'}, '<'),

            # Escaping inside blocktrans works as if it was directly in the
            # template.
            'i18n17': ('{% load i18n %}{% blocktrans with anton|escape as berta %}{{ berta }}{% endblocktrans %}', {'anton': 'α & β'}, u'α &amp; β'),
            'i18n18': ('{% load i18n %}{% blocktrans with anton|force_escape as berta %}{{ berta }}{% endblocktrans %}', {'anton': 'α & β'}, u'α &amp; β'),

            ### HANDLING OF TEMPLATE_STRING_IF_INVALID ###################################

            'invalidstr01': ('{{ var|default:"Foo" }}', {}, ('Foo','INVALID')),
            'invalidstr02': ('{{ var|default_if_none:"Foo" }}', {}, ('','INVALID')),
            'invalidstr03': ('{% for v in var %}({{ v }}){% endfor %}', {}, ''),
            'invalidstr04': ('{% if var %}Yes{% else %}No{% endif %}', {}, 'No'),
            'invalidstr04': ('{% if var|default:"Foo" %}Yes{% else %}No{% endif %}', {}, 'Yes'),
            'invalidstr05': ('{{ var }}', {}, ('', 'INVALID %s', 'var')),
            'invalidstr06': ('{{ var.prop }}', {'var': {}}, ('', 'INVALID %s', 'var.prop')),

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
            'templatetag07': ('{% templatetag openbrace %}', {}, '{'),
            'templatetag08': ('{% templatetag closebrace %}', {}, '}'),
            'templatetag09': ('{% templatetag openbrace %}{% templatetag openbrace %}', {}, '{{'),
            'templatetag10': ('{% templatetag closebrace %}{% templatetag closebrace %}', {}, '}}'),
            'templatetag11': ('{% templatetag opencomment %}', {}, '{#'),
            'templatetag12': ('{% templatetag closecomment %}', {}, '#}'),

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
            'widthratio10': ('{% widthratio a b 100.0 %}', {'a':50,'b':100}, '50'),
            
            # #10043: widthratio should allow max_width to be a variable
            'widthratio11': ('{% widthratio a b c %}', {'a':50,'b':100, 'c': 100}, '50'),

            ### WITH TAG ########################################################
            'with01': ('{% with dict.key as key %}{{ key }}{% endwith %}', {'dict': {'key':50}}, '50'),
            'with02': ('{{ key }}{% with dict.key as key %}{{ key }}-{{ dict.key }}-{{ key }}{% endwith %}{{ key }}', {'dict': {'key':50}}, ('50-50-50', 'INVALID50-50-50INVALID')),

            'with-error01': ('{% with dict.key xx key %}{{ key }}{% endwith %}', {'dict': {'key':50}}, template.TemplateSyntaxError),
            'with-error02': ('{% with dict.key as %}{{ key }}{% endwith %}', {'dict': {'key':50}}, template.TemplateSyntaxError),

            ### NOW TAG ########################################################
            # Simple case
            'now01': ('{% now "j n Y"%}', {}, str(datetime.now().day) + ' ' + str(datetime.now().month) + ' ' + str(datetime.now().year)),

            # Check parsing of escaped and special characters
            'now02': ('{% now "j "n" Y"%}', {}, template.TemplateSyntaxError),
        #    'now03': ('{% now "j \"n\" Y"%}', {}, str(datetime.now().day) + '"' + str(datetime.now().month) + '"' + str(datetime.now().year)),
        #    'now04': ('{% now "j \nn\n Y"%}', {}, str(datetime.now().day) + '\n' + str(datetime.now().month) + '\n' + str(datetime.now().year))

            ### URL TAG ########################################################
            # Successes
            'url01': ('{% url regressiontests.templates.views.client client.id %}', {'client': {'id': 1}}, '/url_tag/client/1/'),
            'url02': ('{% url regressiontests.templates.views.client_action id=client.id,action="update" %}', {'client': {'id': 1}}, '/url_tag/client/1/update/'),
            'url02a': ('{% url regressiontests.templates.views.client_action client.id,"update" %}', {'client': {'id': 1}}, '/url_tag/client/1/update/'),
            'url03': ('{% url regressiontests.templates.views.index %}', {}, '/url_tag/'),
            'url04': ('{% url named.client client.id %}', {'client': {'id': 1}}, '/url_tag/named-client/1/'),
            'url05': (u'{% url метка_оператора v %}', {'v': u'Ω'}, '/url_tag/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/'),
            'url06': (u'{% url метка_оператора_2 tag=v %}', {'v': u'Ω'}, '/url_tag/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/'),
            'url07': (u'{% url regressiontests.templates.views.client2 tag=v %}', {'v': u'Ω'}, '/url_tag/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/'),
            'url08': (u'{% url метка_оператора v %}', {'v': 'Ω'}, '/url_tag/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/'),
            'url09': (u'{% url метка_оператора_2 tag=v %}', {'v': 'Ω'}, '/url_tag/%D0%AE%D0%BD%D0%B8%D0%BA%D0%BE%D0%B4/%CE%A9/'),

            # Failures
            'url-fail01': ('{% url %}', {}, template.TemplateSyntaxError),
            'url-fail02': ('{% url no_such_view %}', {}, urlresolvers.NoReverseMatch),
            'url-fail03': ('{% url regressiontests.templates.views.client %}', {}, urlresolvers.NoReverseMatch),

            # {% url ... as var %}
            'url-asvar01': ('{% url regressiontests.templates.views.index as url %}', {}, ''),
            'url-asvar02': ('{% url regressiontests.templates.views.index as url %}{{ url }}', {}, '/url_tag/'),
            'url-asvar03': ('{% url no_such_view as url %}{{ url }}', {}, ''),

            ### CACHE TAG ######################################################
            'cache01': ('{% load cache %}{% cache -1 test %}cache01{% endcache %}', {}, 'cache01'),
            'cache02': ('{% load cache %}{% cache -1 test %}cache02{% endcache %}', {}, 'cache02'),
            'cache03': ('{% load cache %}{% cache 2 test %}cache03{% endcache %}', {}, 'cache03'),
            'cache04': ('{% load cache %}{% cache 2 test %}cache04{% endcache %}', {}, 'cache03'),
            'cache05': ('{% load cache %}{% cache 2 test foo %}cache05{% endcache %}', {'foo': 1}, 'cache05'),
            'cache06': ('{% load cache %}{% cache 2 test foo %}cache06{% endcache %}', {'foo': 2}, 'cache06'),
            'cache07': ('{% load cache %}{% cache 2 test foo %}cache07{% endcache %}', {'foo': 1}, 'cache05'),

            # Allow first argument to be a variable.
            'cache08': ('{% load cache %}{% cache time test foo %}cache08{% endcache %}', {'foo': 2, 'time': 2}, 'cache06'),
            'cache09': ('{% load cache %}{% cache time test foo %}cache09{% endcache %}', {'foo': 3, 'time': -1}, 'cache09'),
            'cache10': ('{% load cache %}{% cache time test foo %}cache10{% endcache %}', {'foo': 3, 'time': -1}, 'cache10'),

            # Raise exception if we don't have at least 2 args, first one integer.
            'cache11': ('{% load cache %}{% cache %}{% endcache %}', {}, template.TemplateSyntaxError),
            'cache12': ('{% load cache %}{% cache 1 %}{% endcache %}', {}, template.TemplateSyntaxError),
            'cache13': ('{% load cache %}{% cache foo bar %}{% endcache %}', {}, template.TemplateSyntaxError),
            'cache14': ('{% load cache %}{% cache foo bar %}{% endcache %}', {'foo': 'fail'}, template.TemplateSyntaxError),
            'cache15': ('{% load cache %}{% cache foo bar %}{% endcache %}', {'foo': []}, template.TemplateSyntaxError),

            # Regression test for #7460.
            'cache16': ('{% load cache %}{% cache 1 foo bar %}{% endcache %}', {'foo': 'foo', 'bar': 'with spaces'}, ''),

            ### AUTOESCAPE TAG ##############################################
            'autoescape-tag01': ("{% autoescape off %}hello{% endautoescape %}", {}, "hello"),
            'autoescape-tag02': ("{% autoescape off %}{{ first }}{% endautoescape %}", {"first": "<b>hello</b>"}, "<b>hello</b>"),
            'autoescape-tag03': ("{% autoescape on %}{{ first }}{% endautoescape %}", {"first": "<b>hello</b>"}, "&lt;b&gt;hello&lt;/b&gt;"),

            # Autoescape disabling and enabling nest in a predictable way.
            'autoescape-tag04': ("{% autoescape off %}{{ first }} {% autoescape  on%}{{ first }}{% endautoescape %}{% endautoescape %}", {"first": "<a>"}, "<a> &lt;a&gt;"),

            'autoescape-tag05': ("{% autoescape on %}{{ first }}{% endautoescape %}", {"first": "<b>first</b>"}, "&lt;b&gt;first&lt;/b&gt;"),

            # Strings (ASCII or unicode) already marked as "safe" are not
            # auto-escaped
            'autoescape-tag06': ("{{ first }}", {"first": mark_safe("<b>first</b>")}, "<b>first</b>"),
            'autoescape-tag07': ("{% autoescape on %}{{ first }}{% endautoescape %}", {"first": mark_safe(u"<b>Apple</b>")}, u"<b>Apple</b>"),

            # Literal string arguments to filters, if used in the result, are
            # safe.
            'autoescape-tag08': (r'{% autoescape on %}{{ var|default_if_none:" endquote\" hah" }}{% endautoescape %}', {"var": None}, ' endquote" hah'),

            # Objects which return safe strings as their __unicode__ method
            # won't get double-escaped.
            'autoescape-tag09': (r'{{ unsafe }}', {'unsafe': filters.UnsafeClass()}, 'you &amp; me'),
            'autoescape-tag10': (r'{{ safe }}', {'safe': filters.SafeClass()}, 'you &gt; me'),

            # The "safe" and "escape" filters cannot work due to internal
            # implementation details (fortunately, the (no)autoescape block
            # tags can be used in those cases)
            'autoescape-filtertag01': ("{{ first }}{% filter safe %}{{ first }} x<y{% endfilter %}", {"first": "<a>"}, template.TemplateSyntaxError),
        }

if __name__ == "__main__":
    unittest.main()
