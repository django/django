"""
Unit tests for template.py

These tests assume the following template syntax:

FILTER_SEPARATOR = '|'
VARIABLE_ATTRIBUTE_SEPARATOR = '.'
BLOCK_TAG_START = '{%'
BLOCK_TAG_END = '%}'
VARIABLE_TAG_START = '{{'
VARIABLE_TAG_END = '}}'
"""

from django.core import template
import unittest

class RandomSyntaxErrorsCheck(unittest.TestCase):

    def testTagsOnOneLine(self):
        "Tags straddling more than one line are not interpreted"
        c = template.Context({'key':'value'})
        t = template.Template('<h1>{{key\n}}</h1>')
        expected = '<h1>{{key\n}}</h1>'
        self.assertEqual(expected, t.render(c))

class PlainTextCheck(unittest.TestCase):

    def testPlainText(self):
        "Plain text should go through the template parser untouched"
        c = template.Context()
        t = template.Template('<h1>Success</h1>')
        expected = '<h1>Success</h1>'
        self.assertEqual(expected, t.render(c))

class VariableSubstitutionCheck(unittest.TestCase):

    def testSingleTag(self):
        "Variables should be replaced with their value in the current context"
        c = template.Context({'headline':'Success'})
        t = template.Template('<h1>{{headline}}</h1>')
        expected = '<h1>Success</h1>'
        self.assertEqual(expected, t.render(c))

    def testDoubleTag(self):
        "More than one replacement variable is allowed in a template"
        c = template.Context({'firsttag':'it', 'secondtag':'worked'})
        t = template.Template('<h1>{{firsttag}} {{secondtag}}</h1>')
        expected = '<h1>it worked</h1>'
        self.assertEqual(expected, t.render(c))

    def testNonexistentVariable(self):
        "Fail silently when a variable is not found in the current context"
        c = template.Context({})
        t = template.Template('<h1>{{unknownvar}}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testVariablesWithSpaces(self):
        "A replacement-variable tag may not contain more than one word"
        t = '<h1>{{multi word tag}}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testEmptyTag(self):
        "Raise TemplateSyntaxError for empty variable tags"
        t = '{{ }}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)
        t = '{{              }}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testIntegerContextValue(self):
        "Accept integers as variable values"
        c = template.Context({'var':55})
        t = template.Template('<h1>{{var}}</h1>')
        expected = '<h1>55</h1>'
        self.assertEqual(expected, t.render(c))

    def textIntegerContextKey(self):
        "Accept integers as variable keys"
        c = template.Context({55:'var'})
        t = template.Template('<h1>{{55}}</h1>')
        expected = '<h1>var</h1>'
        self.assertEqual(expected, t.render(c))

    def testVariableAttributeAccess1(self):
        "Attribute syntax allows a template to call an object's attribute"
        class AClass: pass
        obj = AClass()
        obj.att = 'attvalue'
        c = template.Context({'var':obj})
        t = template.Template('<h1>{{ var.att }}</h1>')
        expected = '<h1>attvalue</h1>'
        self.assertEqual(expected, t.render(c))

    def testVariableAttributeAccess2(self):
        "Attribute syntax allows a template to call an object's attribute (with getattr defined)"
        class AClass:
            def __getattr__(self, attr):
                return "attvalue"
        obj = AClass()
        c = template.Context({'var':obj})
        t = template.Template('<h1>{{ var.att }}</h1>')
        expected = '<h1>attvalue</h1>'
        self.assertEqual(expected, t.render(c))

    def testVariableAttributeAccessMultiple(self):
        "Multiple levels of attribute access are allowed"
        class AClass: pass
        obj = AClass()
        obj.article = AClass()
        obj.article.section = AClass()
        obj.article.section.title = 'Headline'
        c = template.Context({'obj':obj})
        t = template.Template('<h1>{{ obj.article.section.title }}</h1>')
        expected = '<h1>Headline</h1>'
        self.assertEqual(expected, t.render(c))

    def testNonexistentVariableAttributeObject(self):
        "Fail silently when a variable's attribute isn't found"
        class AClass: pass
        obj = AClass()
        obj.att = 'attvalue'
        c = template.Context({'var':obj})
        t = template.Template('<h1>{{ var.nonexistentatt }}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testIllegalUnderscoreInVariableName(self):
        "Raise TemplateSyntaxError when trying to access a variable beginning with an underscore"
        t = '<h1>{{ var._att }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)
        t = '<h1>{{ _att }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testIllegalCharacterInVariableName(self):
        "Raise TemplateSyntaxError when trying to access a variable containing an illegal character"
        t = '<h1>{{ (blah }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)
        t = '<h1>{{ (blah.test) }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)
        t = '<h1>{{ bl(ah.test) }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testVariableAttributeDictionary(self):
        "Attribute syntax allows a template to call a dictionary key's value"
        obj = {'att':'attvalue'}
        c = template.Context({'var':obj})
        t = template.Template('<h1>{{ var.att }}</h1>')
        expected = '<h1>attvalue</h1>'
        self.assertEqual(expected, t.render(c))

    def testNonexistentVariableAttributeDictionary(self):
        "Fail silently when a variable's dictionary key isn't found"
        obj = {'att':'attvalue'}
        c = template.Context({'var':obj})
        t = template.Template('<h1>{{ var.nonexistentatt }}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testVariableAttributeCallable(self):
        "Attribute syntax allows a template to call a simple method"
        class AClass:
            def hello(self): return 'hi'
        obj = AClass()
        c = template.Context({'var':obj})
        t = template.Template('<h1>{{ var.hello }}</h1>')
        expected = '<h1>hi</h1>'
        self.assertEqual(expected, t.render(c))

    def testVariableAttributeCallableWrongArguments(self):
        "Fail silently when accessing a non-simple method"
        class AClass:
            def hello(self, name): return 'hi, %s' % name
        obj = AClass()
        c = template.Context({'var':obj})
        t = template.Template('<h1>{{ var.hello }}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

class VariableFiltersCheck(unittest.TestCase):

    def setUp(self):
        self.c = template.Context({'var':'Hello There Programmer'})

    def tearDown(self):
        self.c = None

    def testUpper(self):
        "The 'upper' filter converts a string into all uppercase"
        t = template.Template('<h1>{{ var|upper }}</h1>')
        expected = '<h1>HELLO THERE PROGRAMMER</h1>'
        self.assertEqual(expected, t.render(self.c))

    def testLower(self):
        "The 'lower' filter converts a string into all lowercase"
        t = template.Template('<h1>{{ var|lower }}</h1>')
        expected = '<h1>hello there programmer</h1>'
        self.assertEqual(expected, t.render(self.c))

    def testUpperThenLower(self):
        "Filters may be applied in succession (upper|lower)"
        t = template.Template('<h1>{{ var|upper|lower }}</h1>')
        expected = '<h1>hello there programmer</h1>'
        self.assertEqual(expected, t.render(self.c))

    def testLowerThenUpper(self):
        "Filters may be applied in succession (lower|upper)"
        t = template.Template('<h1>{{ var|lower|upper }}</h1>')
        expected = '<h1>HELLO THERE PROGRAMMER</h1>'
        self.assertEqual(expected, t.render(self.c))

    def testSpaceBetweenVariableAndFilterPipe(self):
        "Raise TemplateSyntaxError for space between a variable and filter pipe"
        t = '<h1>{{ var |lower }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testSpaceBetweenFilterPipeAndFilterName1(self):
        "Raise TemplateSyntaxError for space after a filter pipe"
        t = '<h1>{{ var| lower }}</h1>'
        expected = '<h1>Hello There Programmer</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testNonexistentFilter(self):
        "Raise TemplateSyntaxError for a nonexistent filter"
        t = '<h1>{{ var|nonexistentfilter }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testDefaultFilter1(self):
        "Ignore the default argument when a variable passed through the 'default' filter already exists"
        c = template.Context({'var':'Variable'})
        t = template.Template('<h1>{{ var|default:"Default" }}</h1>')
        expected = '<h1>Variable</h1>'
        self.assertEqual(expected, t.render(c))

    def testDefaultFilter2(self):
        "Use the default argument when a variable passed through the 'default' filter doesn't exist"
        c = template.Context({'var':'Variable'})
        t = template.Template('<h1>{{ nonvar|default:"Default" }}</h1>')
        expected = '<h1>Default</h1>'
        self.assertEqual(expected, t.render(c))

    def testDefaultFilter3(self):
        "Use the default argument when a variable passed through the 'default' filter doesn't exist (spaces)"
        c = template.Context({'var':'Variable'})
        t = template.Template('<h1>{{ nonvar|default:"Default value" }}</h1>')
        expected = '<h1>Default value</h1>'
        self.assertEqual(expected, t.render(c))

    def testDefaultFilter4(self):
        "Use the default argument when a variable passed through the 'default' filter doesn't exist (quoted)"
        c = template.Context({'var':'Variable'})
        t = template.Template('<h1>{{ nonvar|default:"Default \"quoted\" value" }}</h1>')
        expected = '<h1>Default "quoted" value</h1>'
        self.assertEqual(expected, t.render(c))

    def testDefaultFilter4(self):
        "Use the default argument when a variable passed through the 'default' filter doesn't exist (escaped backslash)"
        c = template.Context({'var':'Variable'})
        t = template.Template('<h1>{{ nonvar|default:"Default \\\\ slash" }}</h1>')
        expected = '<h1>Default \\ slash</h1>'
        self.assertEqual(expected, t.render(c))

    def testDefaultFilter4(self):
        "Use the default argument when a variable passed through the 'default' filter doesn't exist (single backslash)"
        t = '<h1>{{ nonvar|default:"Default \\ slash" }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testIllegalCharacterInFilterName(self):
        "Raise TemplateSyntaxError when trying to access a filter containing an illegal character"
        t = '<h1>{{ blah|(lower) }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)
        t = '<h1>{{ blah|low(er) }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

class BlockTagCheck(unittest.TestCase):

    def testNonexistentTag(self):
        "Raise TemplateSyntaxError for invalid block tags"
        t = '<h1>{% not-a-tag %}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testEmptyTag(self):
        "Raise TemplateSyntaxError for empty block tags"
        t = '{% %}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

class FirstOfCheck(unittest.TestCase):

    def testFirstOfDisplaysFirstIfSet(self):
        "A firstof tag should display the first item if it evaluates to true somehow"
        c = template.Context({'first': 'one', 'second': 'two'})
        t = template.Template('<h1>{% firstof first second %}</h1>')
        expected = '<h1>one</h1>'
        self.assertEqual(expected, t.render(c))

    def testFirstOfDisplaysSecondIfFirstIsFalse(self):
        "A firstof tag should display the second item if it evaluates to true and the first is false"
        c = template.Context({'first': '', 'second': 'two'})
        t = template.Template('<h1>{% firstof first second %}</h1>')
        expected = '<h1>two</h1>'
        self.assertEqual(expected, t.render(c))

    def testFirstOfRaisesErrorIfEmpty(self):
        "A firstof tag should raise a syntax error if it doesn't have any arguments"
        t = '{% firstof %}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testFirstOfDoesNothingIfAllAreFalse(self):
        "A firstof tag should display nothing if no arguments evaluate to true"
        c = template.Context({'first': '', 'second': False})
        t = template.Template('<h1>{% firstof first second third %}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testFirstOfWorksWithInts(self):
        "Can a firstof tag display an integer?"
        c = template.Context({'first': 1, 'second': False})
        t = template.Template('<h1>{% firstof first second %}</h1>')
        expected = '<h1>1</h1>'
        self.assertEqual(expected, t.render(c))

class IfStatementCheck(unittest.TestCase):

    def testSingleIfStatementTrue(self):
        "An if statement should display its contents if the test evaluates true"
        c = template.Context({'test':True})
        t = template.Template('<h1>{% if test %}Yes{% endif %}</h1>')
        expected = '<h1>Yes</h1>'
        self.assertEqual(expected, t.render(c))

    def testSingleIfStatementFalse(self):
        "An if statement should not display its contents if the test is false"
        c = template.Context({'test':False})
        t = template.Template('<h1>{% if test %}Should not see this{% endif %}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testNestedIfStatementTrueThenTrue(self):
        "Nested if statements should work properly (case 1)"
        c = template.Context({'test1':True, 'test2':True})
        t = template.Template('<h1>{% if test1 %} First {% if test2 %} Second {% endif %} First again {% endif %}</h1>')
        expected = '<h1> First  Second  First again </h1>'
        self.assertEqual(expected, t.render(c))

    def testNestedIfStatementTrueThenFalse(self):
        "Nested if statements should work properly (case 2)"
        c = template.Context({'test1':True, 'test2':False})
        t = template.Template('<h1>{% if test1 %} First {% if test2 %} Second {% endif %} First again {% endif %}</h1>')
        expected = '<h1> First  First again </h1>'
        self.assertEqual(expected, t.render(c))

    def testNestedIfStatementFalseThenTrue(self):
        "Nested if statements should work properly (case 3)"
        c = template.Context({'test1':False, 'test2':True})
        t = template.Template('<h1>{% if test1 %} First {% if test2 %} Second {% endif %} First again {% endif %}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testNestedIfStatementFalseThenFalse(self):
        "Nested if statements should work properly (case 4)"
        c = template.Context({'test1':False, 'test2':False})
        t = template.Template('<h1>{% if test1 %} First {% if test2 %} Second {% endif %} First again {% endif %}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testElseIfTrue(self):
        "An else statement should not execute if the test evaluates to true"
        c = template.Context({'test':True})
        t = template.Template('<h1>{% if test %}Correct{% else %}Incorrect{% endif %}</h1>')
        expected = '<h1>Correct</h1>'
        self.assertEqual(expected, t.render(c))

    def testElseIfFalse(self):
        "An else statement should execute if the test evaluates to false"
        c = template.Context({'test':False})
        t = template.Template('<h1>{% if test %}Incorrect{% else %}Correct{% endif %}</h1>')
        expected = '<h1>Correct</h1>'
        self.assertEqual(expected, t.render(c))

    def testNonClosedIfTag(self):
        "Raise TemplateSyntaxError for non-closed 'if' tags"
        c = template.Context({'test':True})
        t = '<h1>{% if test %}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testNonexistentTest(self):
        "Fail silently when an if statement accesses a nonexistent test"
        c = template.Context({'var':'value'})
        t = template.Template('<h1>{% if nonexistent %}Hello{% endif %}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testIfTagNoArgs(self):
        "If statements must have one argument (case 1)"
        t = '<h1>{% if %}Hello{% endif %}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testIfTagManyArgs(self):
        "If statements must have one argument (case 2)"
        t = '<h1>{% if multiple tests %}Hello{% endif %}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testAttributeAccessInIfNode(self):
        "An if node should resolve a variable's attributes before checking it as a test"
        class AClass: pass
        obj = AClass()
        obj.article = AClass()
        obj.article.section = AClass()
        obj.article.section.title = 'Headline'
        c = template.Context({'obj':obj})
        t = template.Template('<h1>{% if obj.article.section.title %}Hello{% endif %}</h1>')
        expected = '<h1>Hello</h1>'
        self.assertEqual(expected, t.render(c))
        t = template.Template('<h1>{% if obj.article.section.not_here %}Hello{% endif %}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testIfNot(self):
        "If statements supports 'not' as an optional argument"
        t = template.Template('{% if not a %}Not a{% endif %}')
        c = template.Context({'a': False})
        expected = 'Not a'
        self.assertEqual(expected, t.render(c))
        c['a'] = True
        expected = ''
        self.assertEqual(expected, t.render(c))

    def testIfOr(self):
        "If statements support 'or'"
        t = template.Template('{% if a or b %}Hello{% endif %}')
        c = template.Context({'a': False, 'b': True})
        expected = 'Hello'
        self.assertEqual(expected, t.render(c))
        c['b'] = False
        expected = ''
        self.assertEqual(expected, t.render(c))

    def testIfOrNot(self):
        "If statements support 'or' clauses with optional 'not's"
        t = template.Template('{% if a or not b or c%}Hello{% endif %}')
        c = template.Context({'a': False, 'b': False, 'c': False})
        expected = 'Hello'
        self.assertEqual(expected, t.render(c))
        c['b'] = True
        expected = ''
        self.assertEqual(expected, t.render(c))

class ForLoopCheck(unittest.TestCase):

    def testNormalForLoop(self):
        "A for loop should work as expected, given one or more values"
        c = template.Context({'pieces': ('1', '2', '3')})
        t = template.Template('<h1>{% for piece in pieces %}{{ piece }}{% endfor %}</h1>')
        expected = '<h1>123</h1>'
        self.assertEqual(expected, t.render(c))

    def testBlankForLoop(self):
        "A for loop should work as expected, given an empty list"
        c = template.Context({'pieces': []})
        t = template.Template('<h1>{% for piece in pieces %}{{ piece }}{% endfor %}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testInvalidForTagFourWords(self):
        "Raise TemplateSyntaxError if a 'for' statement is not exactly 4 words"
        t = '<h1>{% for article %}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testInvalidForTagThirdWord(self):
        "Raise TemplateSyntaxError if 3rd word in a 'for' statement isn't 'in'"
        t = '<h1>{% for article NOTIN blah %}{% endfor %}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testNonClosedForTag(self):
        "Raise TemplateSyntaxError for non-closed 'for' tags"
        t = '<h1>{% for i in numbers %}{{ i }}</h1>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testNonexistentVariable1(self):
        "Fail silently in loops with nonexistent variables in defn"
        c = template.Context({'var':'value'})
        t = template.Template('<h1>{% for i in nonexistent %}<p>{{ var }}</p>{% endfor %}</h1>')
        expected = '<h1></h1>'
        self.assertEqual(expected, t.render(c))

    def testNonexistentVariable2(self):
        "Raise TemplateSyntaxError in loops with nonexistent variables in loop"
        c = template.Context({'set':('val1', 'val2')})
        t = template.Template('<h1>{% for i in set %}<p>{{ nonexistent }}</p>{% endfor %}</h1>')
        expected = '<h1><p></p><p></p></h1>'
        self.assertEqual(expected, t.render(c))

    def testAttributeAccessInForNode(self):
        "A for node should resolve a variable's attributes before looping through it"
        c = template.Context({'article': {'authors':('Simon', 'Adrian')}})
        t = template.Template('<p>{% for i in article.authors %}{{ i }}{% endfor %}</p>')
        self.assertEqual('<p>SimonAdrian</p>', t.render(c))
        t = template.Template('<p>{% for i in article.nonexistent %}{{ i }}{% endfor %}</p>')
        self.assertEqual('<p></p>', t.render(c))

    def testForLoopFirst(self):
        "A for loop's 'first' variable should work as expected"
        c = template.Context({'pieces': ('1', '2', '3')})
        t = template.Template('<h1>{% for piece in pieces %}{% if forloop.first %}<h2>First</h2>{% endif %}{{ piece }}{% endfor %}</h1>')
        expected = '<h1><h2>First</h2>123</h1>'
        self.assertEqual(expected, t.render(c))

    def testForLoopLast(self):
        "A for loop's 'last' variable should work as expected"
        c = template.Context({'pieces': ('1', '2', '3')})
        t = template.Template('<h1>{% for piece in pieces %}{% if forloop.last %}<h2>Last</h2>{% endif %}{{ piece }}{% endfor %}</h1>')
        expected = '<h1>12<h2>Last</h2>3</h1>'
        self.assertEqual(expected, t.render(c))

class CycleNodeCheck(unittest.TestCase):

    def testNormalUsage(self):
        "A cycle tag should work as expected"
        c = template.Context({'set':range(10)})
        t = template.Template('{% for i in set %}{% cycle red, green %}-{{ i }} {% endfor %}')
        expected = 'red-0 green-1 red-2 green-3 red-4 green-5 red-6 green-7 red-8 green-9 '
        self.assertEqual(expected, t.render(c))

    def testNoArguments(self):
        "Raise TemplateSyntaxError in cycle tags with no arguments"
        t = '{% cycle %}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testOneArgument(self):
        "Raise TemplateSyntaxError in cycle tags with only one argument"
        t = '{% cycle hello %}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testExtraInitialSpaces(self):
        "Extra spaces around cycle tags and their arguments should be ignored"
        c = template.Context({'set':range(5)})
        t = template.Template('{% for i in set %}{% cycle  red, green %}{% endfor %}')
        expected = 'redgreenredgreenred'
        self.assertEqual(expected, t.render(c))

class TemplateTagNodeCheck(unittest.TestCase):

    def testNormalUsage(self):
        "A templatetag tag should work as expected"
        c = template.Context()
        t = template.Template('{% templatetag openblock %}{% templatetag closeblock %}{% templatetag openvariable %}{% templatetag closevariable %}')
        expected = '{%%}{{}}'
        self.assertEqual(expected, t.render(c))

    def testNoArguments(self):
        "Raise TemplateSyntaxError in templatetag tags with no arguments"
        t = '{% templatetag %}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testTwoArguments(self):
        "Raise TemplateSyntaxError in templatetag tags with more than one argument"
        t = '{% templatetag hello goodbye %}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)
        t = '{% templatetag hello goodbye helloagain %}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

    def testBadArgument(self):
        "Raise TemplateSyntaxError in templatetag tags with invalid arguments"
        t = '{% templatetag hello %}'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

class PluginFilterCheck(unittest.TestCase):

    def custom_filter(self, value, arg):
        "Temporary filter used to verify the filter plugin system is working"
        return "_%s_%s_" % (value, arg)

    def testPluginFilter(self):
        "Plugin support allows for custom filters"
        template.register_filter('unittest', self.custom_filter, True)
        c = template.Context({'var':'value'})
        t = template.Template('<body>{{ var|unittest:"hello" }}</body>')
        expected = '<body>_value_hello_</body>'
        self.assertEqual(expected, t.render(c))
        template.unregister_filter('unittest')

    def testUnregisterPluginFilter(self):
        "Plugin support allows custom filters to be unregistered"
        template.register_filter('unittest', self.custom_filter, True)
        c = template.Context({'var':'value'})
        t = template.Template('<body>{{ var|unittest:"hello" }}</body>')
        rendered = t.render(c) # should run with no exception
        template.unregister_filter('unittest')

class PluginTagCheck(unittest.TestCase):

    class CustomNode(template.Node):
        "Prints argument"
        def __init__(self, arg):
            self.arg = arg

        def render(self, context):
            return '_%s_' % self.arg

    def do_custom_node(self, parser, token):
        "Handle the 'unittest' custom tag"
        bits = token.contents.split()
        return self.CustomNode(bits[1])

    def testPluginTag(self):
        "Plugin support allows for custom tags"
        template.register_tag('unittest', self.do_custom_node)
        c = template.Context({})
        t = template.Template('<body>{% unittest hello %}</body>')
        expected = '<body>_hello_</body>'
        self.assertEqual(expected, t.render(c))
        template.unregister_tag('unittest')

    def testUnregisterPluginTag(self):
        "Plugin support allows custom tags to be unregistered"
        template.register_tag('unittest', self.do_custom_node)
        c = template.Context({})
        t = template.Template('<body>{% unittest hello %}</body>')
        rendered = t.render(c) # should run with no exception
        del(t)
        template.unregister_tag('unittest')
        t = '<body>{% unittest hello %}</body>'
        self.assertRaises(template.TemplateSyntaxError, template.Template, t)

class ContextUsageCheck(unittest.TestCase):

    def testVariableContext2(self):
        "Variables should fall through additional block-level contexts"
        c = template.Context({'global':'out', 'set': ('1', '2', '3')})
        t = template.Template('<body><h1>{{ global }}</h1>{% for i in set %}<p>{{ i }} {{ global }}</p>{% endfor %}</body>')
        expected = '<body><h1>out</h1><p>1 out</p><p>2 out</p><p>3 out</p></body>'
        self.assertEqual(expected, t.render(c))

    def testVariableContext2(self):
        "Variables set within a block statement override like-named variables within their scope"
        c = template.Context({'i':'out', 'set': ('1', '2', '3')})
        t = template.Template('<body><h1>{{ i }}</h1>{% for i in set %}<p>{{ i }}</p>{% endfor %}{{ i }}</body>')
        expected = '<body><h1>out</h1><p>1</p><p>2</p><p>3</p>out</body>'
        self.assertEqual(expected, t.render(c))

    def testVariableContextDelete(self):
        "Variables can be deleted from the current context"
        c = template.Context({'a':'first', 'b':'second'})
        del c['a']
        self.assertEqual(c.__repr__(), template.Context({'b':'second'}).__repr__())

    def testInvalidVariableContextDelete(self):
        "Raise KeyError if code tries to delete a variable that doesn't exist in the current context"
        c = template.Context({'a':'first'})
        self.assertRaises(KeyError, c.__delitem__, 'b')

class AdvancedUsageCheck(unittest.TestCase):

    def testIfInsideFor(self):
        "An if statement should be executed repeatedly inside a for statement"
        c = template.Context({'set':(True, False, True, True, False)})
        t = template.Template('<ul>{% for i in set %}{% if i %}<li>1</li>{% endif %}{% endfor %}</ul>')
        expected = '<ul><li>1</li><li>1</li><li>1</li></ul>'
        self.assertEqual(expected, t.render(c))

    def testIfElseInsideFor(self):
        "An if/else statement should be executed repeatedly inside a for statement"
        c = template.Context({'set':(True, False, True, True, False)})
        t = template.Template('<ul>{% for i in set %}<li>{% if i %}1{% else %}0{% endif %}</li>{% endfor %}</ul>')
        expected = '<ul><li>1</li><li>0</li><li>1</li><li>1</li><li>0</li></ul>'
        self.assertEqual(expected, t.render(c))

    def testForInsideIf_True(self):
        "A for loop inside an if statement should be executed if the test=true"
        c = template.Context({'test':True, 'set':('1', '2', '3')})
        t = template.Template('<body>{% if test %}<ul>{% for i in set %}<li>{{ i }}</li>{% endfor %}</ul>{% endif %}</body>')
        expected = '<body><ul><li>1</li><li>2</li><li>3</li></ul></body>'
        self.assertEqual(expected, t.render(c))

    def testForInsideIf_False(self):
        "A for loop inside an if statement shouldn't be executed if the test=false"
        c = template.Context({'test':False, 'set':('1', '2', '3')})
        t = template.Template('<body>{% if test %}<ul>{% for i in set %}<li>{{ i }}</li>{% endfor %}</ul>{% endif %}</body>')
        expected = '<body></body>'
        self.assertEqual(expected, t.render(c))

    def testForInsideIfInsideFor(self):
        "A for loop inside an if statement inside a for loop should work properly"
        c = template.Context({'set1': (True, False, False, False, True), 'set2': ('1', '2', '3')})
        t = template.Template('<body>{% for i in set1 %}{% if i %}{% for j in set2 %}{{ j }}{% endfor %}{% endif %}{% endfor %}</body>')
        expected = '<body>123123</body>'
        self.assertEqual(expected, t.render(c))

    def testMultipleRendersWhenCompiled(self):
        "A template can render multiple contexts without having to be recompiled"
        t = template.Template('<body>{% for i in set1 %}{% if i %}{% for j in set2 %}{{ j }}{% endfor %}{% endif %}{% endfor %}</body>')
        c = template.Context({'set1': (True, False, False, False, False), 'set2': ('1', '2', '3')})
        self.assertEqual('<body>123</body>', t.render(c))
        c = template.Context({'set1': (True, True, False, False, False), 'set2': ('1', '2', '3')})
        self.assertEqual('<body>123123</body>', t.render(c))
        c = template.Context({'set1': (True, True, True, False, False), 'set2': ('1', '2', '3')})
        self.assertEqual('<body>123123123</body>', t.render(c))
        c = template.Context({'set1': (True, True, True, True, False), 'set2': ('1', '2', '3')})
        self.assertEqual('<body>123123123123</body>', t.render(c))
        c = template.Context({'set1': (True, True, True, True, True), 'set2': ('1', '2', '3')})
        self.assertEqual('<body>123123123123123</body>', t.render(c))

def tests():
    s = unittest.TestLoader().loadTestsFromName(__name__)
    unittest.TextTestRunner(verbosity=0).run(s)

if __name__ == "__main__":
    tests()
