from django.template import Context, Template
from django.test import SimpleTestCase

from ..utils import setup


class IfChangedTagTests(SimpleTestCase):

    @setup({'ifchanged01': '{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% endfor %}'})
    def test_ifchanged01(self):
        output = self.engine.render_to_string('ifchanged01', {'num': (1, 2, 3)})
        self.assertEqual(output, '123')

    @setup({'ifchanged02': '{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% endfor %}'})
    def test_ifchanged02(self):
        output = self.engine.render_to_string('ifchanged02', {'num': (1, 1, 3)})
        self.assertEqual(output, '13')

    @setup({'ifchanged03': '{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}{% endfor %}'})
    def test_ifchanged03(self):
        output = self.engine.render_to_string('ifchanged03', {'num': (1, 1, 1)})
        self.assertEqual(output, '1')

    @setup({'ifchanged04': '{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}'
                           '{% for x in numx %}{% ifchanged %}{{ x }}{% endifchanged %}'
                           '{% endfor %}{% endfor %}'})
    def test_ifchanged04(self):
        output = self.engine.render_to_string('ifchanged04', {'num': (1, 2, 3), 'numx': (2, 2, 2)})
        self.assertEqual(output, '122232')

    @setup({'ifchanged05': '{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}'
                           '{% for x in numx %}{% ifchanged %}{{ x }}{% endifchanged %}'
                           '{% endfor %}{% endfor %}'})
    def test_ifchanged05(self):
        output = self.engine.render_to_string('ifchanged05', {'num': (1, 1, 1), 'numx': (1, 2, 3)})
        self.assertEqual(output, '1123123123')

    @setup({'ifchanged06': '{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}'
                           '{% for x in numx %}{% ifchanged %}{{ x }}{% endifchanged %}'
                           '{% endfor %}{% endfor %}'})
    def test_ifchanged06(self):
        output = self.engine.render_to_string('ifchanged06', {'num': (1, 1, 1), 'numx': (2, 2, 2)})
        self.assertEqual(output, '1222')

    @setup({'ifchanged07': '{% for n in num %}{% ifchanged %}{{ n }}{% endifchanged %}'
                           '{% for x in numx %}{% ifchanged %}{{ x }}{% endifchanged %}'
                           '{% for y in numy %}{% ifchanged %}{{ y }}{% endifchanged %}'
                           '{% endfor %}{% endfor %}{% endfor %}'})
    def test_ifchanged07(self):
        output = self.engine.render_to_string('ifchanged07', {'num': (1, 1, 1), 'numx': (2, 2, 2), 'numy': (3, 3, 3)})
        self.assertEqual(output, '1233323332333')

    @setup({'ifchanged08': '{% for data in datalist %}{% for c,d in data %}'
                           '{% if c %}{% ifchanged %}{{ d }}{% endifchanged %}'
                           '{% endif %}{% endfor %}{% endfor %}'})
    def test_ifchanged08(self):
        output = self.engine.render_to_string('ifchanged08', {'datalist': [
            [(1, 'a'), (1, 'a'), (0, 'b'), (1, 'c')],
            [(0, 'a'), (1, 'c'), (1, 'd'), (1, 'd'), (0, 'e')]
        ]})
        self.assertEqual(output, 'accd')

    @setup({'ifchanged-param01': '{% for n in num %}{% ifchanged n %}..{% endifchanged %}'
                                 '{{ n }}{% endfor %}'})
    def test_ifchanged_param01(self):
        """
        Test one parameter given to ifchanged.
        """
        output = self.engine.render_to_string('ifchanged-param01', {'num': (1, 2, 3)})
        self.assertEqual(output, '..1..2..3')

    @setup({'ifchanged-param02': '{% for n in num %}{% for x in numx %}{% ifchanged n %}..{% endifchanged %}'
                                 '{{ x }}{% endfor %}{% endfor %}'})
    def test_ifchanged_param02(self):
        output = self.engine.render_to_string('ifchanged-param02', {'num': (1, 2, 3), 'numx': (5, 6, 7)})
        self.assertEqual(output, '..567..567..567')

    @setup({'ifchanged-param03': '{% for n in num %}{{ n }}{% for x in numx %}'
                                 '{% ifchanged x n %}{{ x }}{% endifchanged %}'
                                 '{% endfor %}{% endfor %}'})
    def test_ifchanged_param03(self):
        """
        Test multiple parameters to ifchanged.
        """
        output = self.engine.render_to_string('ifchanged-param03', {'num': (1, 1, 2), 'numx': (5, 6, 6)})
        self.assertEqual(output, '156156256')

    @setup({'ifchanged-param04': '{% for d in days %}{% ifchanged %}{{ d.day }}{% endifchanged %}'
                                 '{% for h in d.hours %}{% ifchanged d h %}{{ h }}{% endifchanged %}'
                                 '{% endfor %}{% endfor %}'})
    def test_ifchanged_param04(self):
        """
        Test a date+hour like construct, where the hour of the last day is
        the same but the date had changed, so print the hour anyway.
        """
        output = self.engine.render_to_string(
            'ifchanged-param04',
            {'days': [{'hours': [1, 2, 3], 'day': 1}, {'hours': [3], 'day': 2}]},
        )
        self.assertEqual(output, '112323')

    @setup({'ifchanged-param05': '{% for d in days %}{% ifchanged d.day %}{{ d.day }}{% endifchanged %}'
                                 '{% for h in d.hours %}{% ifchanged d.day h %}{{ h }}{% endifchanged %}'
                                 '{% endfor %}{% endfor %}'})
    def test_ifchanged_param05(self):
        """
        Logically the same as above, just written with explicit ifchanged
        for the day.
        """
        output = self.engine.render_to_string(
            'ifchanged-param05',
            {'days': [{'hours': [1, 2, 3], 'day': 1}, {'hours': [3], 'day': 2}]},
        )
        self.assertEqual(output, '112323')

    @setup({'ifchanged-else01': '{% for id in ids %}{{ id }}'
                                '{% ifchanged id %}-first{% else %}-other{% endifchanged %}'
                                ',{% endfor %}'})
    def test_ifchanged_else01(self):
        """
        Test the else clause of ifchanged.
        """
        output = self.engine.render_to_string('ifchanged-else01', {'ids': [1, 1, 2, 2, 2, 3]})
        self.assertEqual(output, '1-first,1-other,2-first,2-other,2-other,3-first,')

    @setup({'ifchanged-else02': '{% for id in ids %}{{ id }}-'
                                '{% ifchanged id %}{% cycle red,blue %}{% else %}grey{% endifchanged %}'
                                ',{% endfor %}'})
    def test_ifchanged_else02(self):
        output = self.engine.render_to_string('ifchanged-else02', {'ids': [1, 1, 2, 2, 2, 3]})
        self.assertEqual(output, '1-red,1-grey,2-blue,2-grey,2-grey,3-red,')

    @setup({'ifchanged-else03': '{% for id in ids %}{{ id }}'
                                '{% ifchanged id %}-{% cycle red,blue %}{% else %}{% endifchanged %}'
                                ',{% endfor %}'})
    def test_ifchanged_else03(self):
        output = self.engine.render_to_string('ifchanged-else03', {'ids': [1, 1, 2, 2, 2, 3]})
        self.assertEqual(output, '1-red,1,2-blue,2,2,3-red,')

    @setup({'ifchanged-else04': '{% for id in ids %}'
                                '{% ifchanged %}***{{ id }}*{% else %}...{% endifchanged %}'
                                '{{ forloop.counter }}{% endfor %}'})
    def test_ifchanged_else04(self):
        output = self.engine.render_to_string('ifchanged-else04', {'ids': [1, 1, 2, 2, 2, 3, 4]})
        self.assertEqual(output, '***1*1...2***2*3...4...5***3*6***4*7')

    @setup({'ifchanged-filter-ws': '{% load custom %}{% for n in num %}'
                                   '{% ifchanged n|noop:"x y" %}..{% endifchanged %}{{ n }}'
                                   '{% endfor %}'})
    def test_ifchanged_filter_ws(self):
        """
        Test whitespace in filter arguments
        """
        output = self.engine.render_to_string('ifchanged-filter-ws', {'num': (1, 2, 3)})
        self.assertEqual(output, '..1..2..3')


class IfChangedTests(SimpleTestCase):

    def test_ifchanged_concurrency(self):
        """
        #15849 -- ifchanged should be thread-safe.
        """
        template = Template('[0{% for x in foo %},{% with var=get_value %}{% ifchanged %}{{ var }}{% endifchanged %}{% endwith %}{% endfor %}]')

        # Using generator to mimic concurrency.
        # The generator is not passed to the 'for' loop, because it does a list(values)
        # instead, call gen.next() in the template to control the generator.
        def gen():
            yield 1
            yield 2
            # Simulate that another thread is now rendering.
            # When the IfChangeNode stores state at 'self' it stays at '3' and skip the last yielded value below.
            iter2 = iter([1, 2, 3])
            output2 = template.render(Context({'foo': range(3), 'get_value': lambda: next(iter2)}))
            self.assertEqual(output2, '[0,1,2,3]', 'Expected [0,1,2,3] in second parallel template, got {}'.format(output2))
            yield 3

        gen1 = gen()
        output1 = template.render(Context({'foo': range(3), 'get_value': lambda: next(gen1)}))
        self.assertEqual(output1, '[0,1,2,3]', 'Expected [0,1,2,3] in first template, got {}'.format(output1))

    def test_ifchanged_render_once(self):
        """
        #19890. The content of ifchanged template tag was rendered twice.
        """
        template = Template('{% ifchanged %}{% cycle "1st time" "2nd time" %}{% endifchanged %}')
        output = template.render(Context({}))
        self.assertEqual(output, '1st time')
