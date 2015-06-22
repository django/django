from django.template import TemplateSyntaxError
from django.test import SimpleTestCase, ignore_warnings
from django.utils.deprecation import RemovedInDjango110Warning

from ..utils import setup


class ForTagTests(SimpleTestCase):

    @setup({'for-tag01': '{% for val in values %}{{ val }}{% endfor %}'})
    def test_for_tag01(self):
        output = self.engine.render_to_string('for-tag01', {'values': [1, 2, 3]})
        self.assertEqual(output, '123')

    @setup({'for-tag02': '{% for val in values reversed %}{{ val }}{% endfor %}'})
    def test_for_tag02(self):
        output = self.engine.render_to_string('for-tag02', {'values': [1, 2, 3]})
        self.assertEqual(output, '321')

    @setup({'for-tag-vars01': '{% for val in values %}{{ forloop.counter }}{% endfor %}'})
    def test_for_tag_vars01(self):
        output = self.engine.render_to_string('for-tag-vars01', {'values': [6, 6, 6]})
        self.assertEqual(output, '123')

    @setup({'for-tag-vars02': '{% for val in values %}{{ forloop.counter0 }}{% endfor %}'})
    def test_for_tag_vars02(self):
        output = self.engine.render_to_string('for-tag-vars02', {'values': [6, 6, 6]})
        self.assertEqual(output, '012')

    @setup({'for-tag-vars03': '{% for val in values %}{{ forloop.revcounter }}{% endfor %}'})
    def test_for_tag_vars03(self):
        output = self.engine.render_to_string('for-tag-vars03', {'values': [6, 6, 6]})
        self.assertEqual(output, '321')

    @setup({'for-tag-vars04': '{% for val in values %}{{ forloop.revcounter0 }}{% endfor %}'})
    def test_for_tag_vars04(self):
        output = self.engine.render_to_string('for-tag-vars04', {'values': [6, 6, 6]})
        self.assertEqual(output, '210')

    @setup({'for-tag-vars05': '{% for val in values %}'
                              '{% if forloop.first %}f{% else %}x{% endif %}{% endfor %}'})
    def test_for_tag_vars05(self):
        output = self.engine.render_to_string('for-tag-vars05', {'values': [6, 6, 6]})
        self.assertEqual(output, 'fxx')

    @setup({'for-tag-vars06': '{% for val in values %}'
                              '{% if forloop.last %}l{% else %}x{% endif %}{% endfor %}'})
    def test_for_tag_vars06(self):
        output = self.engine.render_to_string('for-tag-vars06', {'values': [6, 6, 6]})
        self.assertEqual(output, 'xxl')

    @setup({'for-tag-unpack01': '{% for key,value in items %}{{ key }}:{{ value }}/{% endfor %}'})
    def test_for_tag_unpack01(self):
        output = self.engine.render_to_string('for-tag-unpack01', {'items': (('one', 1), ('two', 2))})
        self.assertEqual(output, 'one:1/two:2/')

    @setup({'for-tag-unpack03': '{% for key, value in items %}{{ key }}:{{ value }}/{% endfor %}'})
    def test_for_tag_unpack03(self):
        output = self.engine.render_to_string('for-tag-unpack03', {'items': (('one', 1), ('two', 2))})
        self.assertEqual(output, 'one:1/two:2/')

    @setup({'for-tag-unpack04': '{% for key , value in items %}{{ key }}:{{ value }}/{% endfor %}'})
    def test_for_tag_unpack04(self):
        output = self.engine.render_to_string('for-tag-unpack04', {'items': (('one', 1), ('two', 2))})
        self.assertEqual(output, 'one:1/two:2/')

    @setup({'for-tag-unpack05': '{% for key ,value in items %}{{ key }}:{{ value }}/{% endfor %}'})
    def test_for_tag_unpack05(self):
        output = self.engine.render_to_string('for-tag-unpack05', {'items': (('one', 1), ('two', 2))})
        self.assertEqual(output, 'one:1/two:2/')

    @setup({'for-tag-unpack06': '{% for key value in items %}{{ key }}:{{ value }}/{% endfor %}'})
    def test_for_tag_unpack06(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('for-tag-unpack06', {'items': (('one', 1), ('two', 2))})

    @setup({'for-tag-unpack07': '{% for key,,value in items %}{{ key }}:{{ value }}/{% endfor %}'})
    def test_for_tag_unpack07(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('for-tag-unpack07', {'items': (('one', 1), ('two', 2))})

    @setup({'for-tag-unpack08': '{% for key,value, in items %}{{ key }}:{{ value }}/{% endfor %}'})
    def test_for_tag_unpack08(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.render_to_string('for-tag-unpack08', {'items': (('one', 1), ('two', 2))})

    @setup({'for-tag-unpack09': '{% for val in items %}{{ val.0 }}:{{ val.1 }}/{% endfor %}'})
    def test_for_tag_unpack09(self):
        """
        Ensure that a single loopvar doesn't truncate the list in val.
        """
        output = self.engine.render_to_string('for-tag-unpack09', {'items': (('one', 1), ('two', 2))})
        self.assertEqual(output, 'one:1/two:2/')

    @setup({'for-tag-unpack13': '{% for x,y,z in items %}{{ x }}:{{ y }},{{ z }}/{% endfor %}'})
    def test_for_tag_unpack13(self):
        output = self.engine.render_to_string('for-tag-unpack13', {'items': (('one', 1, 'carrot'), ('two', 2, 'cheese'))})
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'one:1,carrot/two:2,cheese/')
        else:
            self.assertEqual(output, 'one:1,carrot/two:2,cheese/')

    @setup({'for-tag-empty01': '{% for val in values %}{{ val }}{% empty %}empty text{% endfor %}'})
    def test_for_tag_empty01(self):
        output = self.engine.render_to_string('for-tag-empty01', {'values': [1, 2, 3]})
        self.assertEqual(output, '123')

    @setup({'for-tag-empty02': '{% for val in values %}{{ val }}{% empty %}values array empty{% endfor %}'})
    def test_for_tag_empty02(self):
        output = self.engine.render_to_string('for-tag-empty02', {'values': []})
        self.assertEqual(output, 'values array empty')

    @setup({'for-tag-empty03': '{% for val in values %}'
                               '{{ val }}{% empty %}values array not found{% endfor %}'})
    def test_for_tag_empty03(self):
        output = self.engine.render_to_string('for-tag-empty03')
        self.assertEqual(output, 'values array not found')

    @setup({'for-tag-filter-ws': "{% load custom %}{% for x in s|noop:'x y' %}{{ x }}{% endfor %}"})
    def test_for_tag_filter_ws(self):
        """
        #19882
        """
        output = self.engine.render_to_string('for-tag-filter-ws', {'s': 'abc'})
        self.assertEqual(output, 'abc')

    # These tests raise deprecation warnings and will raise an exception
    # in Django 1.10. The existing behavior is silent truncation if the
    # length of loopvars differs to the length of each set of items.
    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'for-tag-unpack10': '{% for x,y in items %}{{ x }}:{{ y }}/{% endfor %}'})
    def test_for_tag_unpack10(self):
        output = self.engine.render_to_string(
            'for-tag-unpack10',
            {'items': (('one', 1, 'carrot'), ('two', 2, 'orange'))},
        )
        self.assertEqual(output, 'one:1/two:2/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'for-tag-unpack11': '{% for x,y,z in items %}{{ x }}:{{ y }},{{ z }}/{% endfor %}'})
    def test_for_tag_unpack11(self):
        output = self.engine.render_to_string(
            'for-tag-unpack11',
            {'items': (('one', 1), ('two', 2))},
        )

        if self.engine.string_if_invalid:
            self.assertEqual(output, 'one:1,INVALID/two:2,INVALID/')
        else:
            self.assertEqual(output, 'one:1,/two:2,/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'for-tag-unpack12': '{% for x,y,z in items %}{{ x }}:{{ y }},{{ z }}/{% endfor %}'})
    def test_for_tag_unpack12(self):
        output = self.engine.render_to_string(
            'for-tag-unpack12',
            {'items': (('one', 1, 'carrot'), ('two', 2))}
        )
        if self.engine.string_if_invalid:
            self.assertEqual(output, 'one:1,carrot/two:2,INVALID/')
        else:
            self.assertEqual(output, 'one:1,carrot/two:2,/')

    @ignore_warnings(category=RemovedInDjango110Warning)
    @setup({'for-tag-unpack14': '{% for x,y in items %}{{ x }}:{{ y }}/{% endfor %}'})
    def test_for_tag_unpack14(self):
        output = self.engine.render_to_string('for-tag-unpack14', {'items': (1, 2)})

        if self.engine.string_if_invalid:
            self.assertEqual(output, 'INVALID:INVALID/INVALID:INVALID/')
        else:
            self.assertEqual(output, ':/:/')
