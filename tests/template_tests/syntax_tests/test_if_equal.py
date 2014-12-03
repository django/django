from django.test import SimpleTestCase

from .utils import render, setup


class IfEqualTagTests(SimpleTestCase):

    @setup({'ifequal01': '{% ifequal a b %}yes{% endifequal %}'})
    def test_ifequal01(self):
        output = render('ifequal01', {'a': 1, 'b': 2})
        self.assertEqual(output, '')

    @setup({'ifequal02': '{% ifequal a b %}yes{% endifequal %}'})
    def test_ifequal02(self):
        output = render('ifequal02', {'a': 1, 'b': 1})
        self.assertEqual(output, 'yes')

    @setup({'ifequal03': '{% ifequal a b %}yes{% else %}no{% endifequal %}'})
    def test_ifequal03(self):
        output = render('ifequal03', {'a': 1, 'b': 2})
        self.assertEqual(output, 'no')

    @setup({'ifequal04': '{% ifequal a b %}yes{% else %}no{% endifequal %}'})
    def test_ifequal04(self):
        output = render('ifequal04', {'a': 1, 'b': 1})
        self.assertEqual(output, 'yes')

    @setup({'ifequal05': '{% ifequal a \'test\' %}yes{% else %}no{% endifequal %}'})
    def test_ifequal05(self):
        output = render('ifequal05', {'a': 'test'})
        self.assertEqual(output, 'yes')

    @setup({'ifequal06': '{% ifequal a \'test\' %}yes{% else %}no{% endifequal %}'})
    def test_ifequal06(self):
        output = render('ifequal06', {'a': 'no'})
        self.assertEqual(output, 'no')

    @setup({'ifequal07': '{% ifequal a "test" %}yes{% else %}no{% endifequal %}'})
    def test_ifequal07(self):
        output = render('ifequal07', {'a': 'test'})
        self.assertEqual(output, 'yes')

    @setup({'ifequal08': '{% ifequal a "test" %}yes{% else %}no{% endifequal %}'})
    def test_ifequal08(self):
        output = render('ifequal08', {'a': 'no'})
        self.assertEqual(output, 'no')

    @setup({'ifequal09': '{% ifequal a "test" %}yes{% else %}no{% endifequal %}'})
    def test_ifequal09(self):
        output = render('ifequal09')
        self.assertEqual(output, 'no')

    @setup({'ifequal10': '{% ifequal a b %}yes{% else %}no{% endifequal %}'})
    def test_ifequal10(self):
        output = render('ifequal10')
        self.assertEqual(output, 'yes')

    # SMART SPLITTING
    @setup({'ifequal-split01': '{% ifequal a "test man" %}yes{% else %}no{% endifequal %}'})
    def test_ifequal_split01(self):
        output = render('ifequal-split01')
        self.assertEqual(output, 'no')

    @setup({'ifequal-split02': '{% ifequal a "test man" %}yes{% else %}no{% endifequal %}'})
    def test_ifequal_split02(self):
        output = render('ifequal-split02', {'a': 'foo'})
        self.assertEqual(output, 'no')

    @setup({'ifequal-split03': '{% ifequal a "test man" %}yes{% else %}no{% endifequal %}'})
    def test_ifequal_split03(self):
        output = render('ifequal-split03', {'a': 'test man'})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-split04': '{% ifequal a \'test man\' %}yes{% else %}no{% endifequal %}'})
    def test_ifequal_split04(self):
        output = render('ifequal-split04', {'a': 'test man'})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-split05': '{% ifequal a \'i "love" you\' %}yes{% else %}no{% endifequal %}'})
    def test_ifequal_split05(self):
        output = render('ifequal-split05', {'a': ''})
        self.assertEqual(output, 'no')

    @setup({'ifequal-split06': '{% ifequal a \'i "love" you\' %}yes{% else %}no{% endifequal %}'})
    def test_ifequal_split06(self):
        output = render('ifequal-split06', {'a': 'i "love" you'})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-split07': '{% ifequal a \'i "love" you\' %}yes{% else %}no{% endifequal %}'})
    def test_ifequal_split07(self):
        output = render('ifequal-split07', {'a': 'i love you'})
        self.assertEqual(output, 'no')

    @setup({'ifequal-split08': r"{% ifequal a 'I\'m happy' %}yes{% else %}no{% endifequal %}"})
    def test_ifequal_split08(self):
        output = render('ifequal-split08', {'a': "I'm happy"})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-split09': r"{% ifequal a 'slash\man' %}yes{% else %}no{% endifequal %}"})
    def test_ifequal_split09(self):
        output = render('ifequal-split09', {'a': 'slash\man'})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-split10': r"{% ifequal a 'slash\man' %}yes{% else %}no{% endifequal %}"})
    def test_ifequal_split10(self):
        output = render('ifequal-split10', {'a': 'slashman'})
        self.assertEqual(output, 'no')

    # NUMERIC RESOLUTION
    @setup({'ifequal-numeric01': '{% ifequal x 5 %}yes{% endifequal %}'})
    def test_ifequal_numeric01(self):
        output = render('ifequal-numeric01', {'x': '5'})
        self.assertEqual(output, '')

    @setup({'ifequal-numeric02': '{% ifequal x 5 %}yes{% endifequal %}'})
    def test_ifequal_numeric02(self):
        output = render('ifequal-numeric02', {'x': 5})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-numeric03': '{% ifequal x 5.2 %}yes{% endifequal %}'})
    def test_ifequal_numeric03(self):
        output = render('ifequal-numeric03', {'x': 5})
        self.assertEqual(output, '')

    @setup({'ifequal-numeric04': '{% ifequal x 5.2 %}yes{% endifequal %}'})
    def test_ifequal_numeric04(self):
        output = render('ifequal-numeric04', {'x': 5.2})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-numeric05': '{% ifequal x 0.2 %}yes{% endifequal %}'})
    def test_ifequal_numeric05(self):
        output = render('ifequal-numeric05', {'x': 0.2})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-numeric06': '{% ifequal x .2 %}yes{% endifequal %}'})
    def test_ifequal_numeric06(self):
        output = render('ifequal-numeric06', {'x': 0.2})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-numeric07': '{% ifequal x 2. %}yes{% endifequal %}'})
    def test_ifequal_numeric07(self):
        output = render('ifequal-numeric07', {'x': 2})
        self.assertEqual(output, '')

    @setup({'ifequal-numeric08': '{% ifequal x "5" %}yes{% endifequal %}'})
    def test_ifequal_numeric08(self):
        output = render('ifequal-numeric08', {'x': 5})
        self.assertEqual(output, '')

    @setup({'ifequal-numeric09': '{% ifequal x "5" %}yes{% endifequal %}'})
    def test_ifequal_numeric09(self):
        output = render('ifequal-numeric09', {'x': '5'})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-numeric10': '{% ifequal x -5 %}yes{% endifequal %}'})
    def test_ifequal_numeric10(self):
        output = render('ifequal-numeric10', {'x': -5})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-numeric11': '{% ifequal x -5.2 %}yes{% endifequal %}'})
    def test_ifequal_numeric11(self):
        output = render('ifequal-numeric11', {'x': -5.2})
        self.assertEqual(output, 'yes')

    @setup({'ifequal-numeric12': '{% ifequal x +5 %}yes{% endifequal %}'})
    def test_ifequal_numeric12(self):
        output = render('ifequal-numeric12', {'x': 5})
        self.assertEqual(output, 'yes')

    # FILTER EXPRESSIONS AS ARGUMENTS
    @setup({'ifequal-filter01': '{% ifequal a|upper "A" %}x{% endifequal %}'})
    def test_ifequal_filter01(self):
        output = render('ifequal-filter01', {'a': 'a'})
        self.assertEqual(output, 'x')

    @setup({'ifequal-filter02': '{% ifequal "A" a|upper %}x{% endifequal %}'})
    def test_ifequal_filter02(self):
        output = render('ifequal-filter02', {'a': 'a'})
        self.assertEqual(output, 'x')

    @setup({'ifequal-filter03': '{% ifequal a|upper b|upper %}x{% endifequal %}'})
    def test_ifequal_filter03(self):
        output = render('ifequal-filter03', {'a': 'x', 'b': 'X'})
        self.assertEqual(output, 'x')

    @setup({'ifequal-filter04': '{% ifequal x|slice:"1" "a" %}x{% endifequal %}'})
    def test_ifequal_filter04(self):
        output = render('ifequal-filter04', {'x': 'aaa'})
        self.assertEqual(output, 'x')

    @setup({'ifequal-filter05': '{% ifequal x|slice:"1"|upper "A" %}x{% endifequal %}'})
    def test_ifequal_filter05(self):
        output = render('ifequal-filter05', {'x': 'aaa'})
        self.assertEqual(output, 'x')


class IfNotEqualTagTests(SimpleTestCase):

    @setup({'ifnotequal01': '{% ifnotequal a b %}yes{% endifnotequal %}'})
    def test_ifnotequal01(self):
        output = render('ifnotequal01', {'a': 1, 'b': 2})
        self.assertEqual(output, 'yes')

    @setup({'ifnotequal02': '{% ifnotequal a b %}yes{% endifnotequal %}'})
    def test_ifnotequal02(self):
        output = render('ifnotequal02', {'a': 1, 'b': 1})
        self.assertEqual(output, '')

    @setup({'ifnotequal03': '{% ifnotequal a b %}yes{% else %}no{% endifnotequal %}'})
    def test_ifnotequal03(self):
        output = render('ifnotequal03', {'a': 1, 'b': 2})
        self.assertEqual(output, 'yes')

    @setup({'ifnotequal04': '{% ifnotequal a b %}yes{% else %}no{% endifnotequal %}'})
    def test_ifnotequal04(self):
        output = render('ifnotequal04', {'a': 1, 'b': 1})
        self.assertEqual(output, 'no')
