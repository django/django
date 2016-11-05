from datetime import date

from django.template import TemplateSyntaxError
from django.test import SimpleTestCase

from ..utils import setup


class RegroupTagTests(SimpleTestCase):

    @setup({'regroup01': ''
                         '{% regroup data by bar as grouped %}'
                         '{% for group in grouped %}'
                         '{{ group.grouper }}:'
                         '{% for item in group.list %}'
                         '{{ item.foo }}'
                         '{% endfor %},'
                         '{% endfor %}'})
    def test_regroup01(self):
        output = self.engine.render_to_string('regroup01', {
            'data': [{'foo': 'c', 'bar': 1},
                     {'foo': 'd', 'bar': 1},
                     {'foo': 'a', 'bar': 2},
                     {'foo': 'b', 'bar': 2},
                     {'foo': 'x', 'bar': 3}],
        })
        self.assertEqual(output, '1:cd,2:ab,3:x,')

    @setup({'regroup02': ''
                         '{% regroup data by bar as grouped %}'
                         '{% for group in grouped %}'
                         '{{ group.grouper }}:'
                         '{% for item in group.list %}'
                         '{{ item.foo }}'
                         '{% endfor %}'
                         '{% endfor %}'})
    def test_regroup02(self):
        """
        Test for silent failure when target variable isn't found
        """
        output = self.engine.render_to_string('regroup02', {})
        self.assertEqual(output, '')

    @setup({'regroup03': ''
                         '{% regroup data by at|date:"m" as grouped %}'
                         '{% for group in grouped %}'
                         '{{ group.grouper }}:'
                         '{% for item in group.list %}'
                         '{{ item.at|date:"d" }}'
                         '{% endfor %},'
                         '{% endfor %}'})
    def test_regroup03(self):
        """
        Regression tests for #17675
        The date template filter has expects_localtime = True
        """
        output = self.engine.render_to_string('regroup03', {
            'data': [{'at': date(2012, 2, 14)},
                     {'at': date(2012, 2, 28)},
                     {'at': date(2012, 7, 4)}],
        })
        self.assertEqual(output, '02:1428,07:04,')

    @setup({'regroup04': ''
                         '{% regroup data by bar|join:"" as grouped %}'
                         '{% for group in grouped %}'
                         '{{ group.grouper }}:'
                         '{% for item in group.list %}'
                         '{{ item.foo|first }}'
                         '{% endfor %},'
                         '{% endfor %}'})
    def test_regroup04(self):
        """
        The join template filter has needs_autoescape = True
        """
        output = self.engine.render_to_string('regroup04', {
            'data': [{'foo': 'x', 'bar': ['ab', 'c']},
                     {'foo': 'y', 'bar': ['a', 'bc']},
                     {'foo': 'z', 'bar': ['a', 'd']}],
        })
        self.assertEqual(output, 'abc:xy,ad:z,')

    # Test syntax errors
    @setup({'regroup05': '{% regroup data by bar as %}'})
    def test_regroup05(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('regroup05')

    @setup({'regroup06': '{% regroup data by bar thisaintright grouped %}'})
    def test_regroup06(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('regroup06')

    @setup({'regroup07': '{% regroup data thisaintright bar as grouped %}'})
    def test_regroup07(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('regroup07')

    @setup({'regroup08': '{% regroup data by bar as grouped toomanyargs %}'})
    def test_regroup08(self):
        with self.assertRaises(TemplateSyntaxError):
            self.engine.get_template('regroup08')

    @setup({'regroup_unpack': '{% regroup data by bar as grouped %}'
                              '{% for grouper, group in grouped %}'
                              '{{ grouper }}:'
                              '{% for item in group %}'
                              '{{ item.foo }}'
                              '{% endfor %},'
                              '{% endfor %}'})
    def test_regroup_unpack(self):
        output = self.engine.render_to_string('regroup_unpack', {
            'data': [
                {'foo': 'c', 'bar': 1},
                {'foo': 'd', 'bar': 1},
                {'foo': 'a', 'bar': 2},
                {'foo': 'b', 'bar': 2},
                {'foo': 'x', 'bar': 3},
            ],
        })
        self.assertEqual(output, '1:cd,2:ab,3:x,')
