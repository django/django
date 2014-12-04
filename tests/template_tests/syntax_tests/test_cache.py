from django.core.cache import cache
from django.template.base import TemplateSyntaxError
from django.template.loader import get_template
from django.test import SimpleTestCase

from ..utils import render, setup


class CacheTagTests(SimpleTestCase):

    def tearDown(self):
        cache.clear()

    @setup({'cache03': '{% load cache %}{% cache 2 test %}cache03{% endcache %}'})
    def test_cache03(self):
        output = render('cache03')
        self.assertEqual(output, 'cache03')

    @setup({
        'cache03': '{% load cache %}{% cache 2 test %}cache03{% endcache %}',
        'cache04': '{% load cache %}{% cache 2 test %}cache04{% endcache %}',
    })
    def test_cache04(self):
        render('cache03')
        output = render('cache04')
        self.assertEqual(output, 'cache03')

    @setup({'cache05': '{% load cache %}{% cache 2 test foo %}cache05{% endcache %}'})
    def test_cache05(self):
        output = render('cache05', {'foo': 1})
        self.assertEqual(output, 'cache05')

    @setup({'cache06': '{% load cache %}{% cache 2 test foo %}cache06{% endcache %}'})
    def test_cache06(self):
        output = render('cache06', {'foo': 2})
        self.assertEqual(output, 'cache06')

    @setup({
        'cache05': '{% load cache %}{% cache 2 test foo %}cache05{% endcache %}',
        'cache07': '{% load cache %}{% cache 2 test foo %}cache07{% endcache %}',
    })
    def test_cache07(self):
        context = {'foo': 1}
        render('cache05', context)
        output = render('cache07', context)
        self.assertEqual(output, 'cache05')

    @setup({
        'cache06': '{% load cache %}{% cache 2 test foo %}cache06{% endcache %}',
        'cache08': '{% load cache %}{% cache time test foo %}cache08{% endcache %}',
    })
    def test_cache08(self):
        """
        Allow first argument to be a variable.
        """
        context = {'foo': 2, 'time': 2}
        render('cache06', context)
        output = render('cache08', context)
        self.assertEqual(output, 'cache06')

    # Raise exception if we don't have at least 2 args, first one integer.
    @setup({'cache11': '{% load cache %}{% cache %}{% endcache %}'})
    def test_cache11(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('cache11')

    @setup({'cache12': '{% load cache %}{% cache 1 %}{% endcache %}'})
    def test_cache12(self):
        with self.assertRaises(TemplateSyntaxError):
            get_template('cache12')

    @setup({'cache13': '{% load cache %}{% cache foo bar %}{% endcache %}'})
    def test_cache13(self):
        with self.assertRaises(TemplateSyntaxError):
            render('cache13')

    @setup({'cache14': '{% load cache %}{% cache foo bar %}{% endcache %}'})
    def test_cache14(self):
        with self.assertRaises(TemplateSyntaxError):
            render('cache14', {'foo': 'fail'})

    @setup({'cache15': '{% load cache %}{% cache foo bar %}{% endcache %}'})
    def test_cache15(self):
        with self.assertRaises(TemplateSyntaxError):
            render('cache15', {'foo': []})

    @setup({'cache16': '{% load cache %}{% cache 1 foo bar %}{% endcache %}'})
    def test_cache16(self):
        """
        Regression test for #7460.
        """
        output = render('cache16', {'foo': 'foo', 'bar': 'with spaces'})
        self.assertEqual(output, '')

    @setup({'cache17': '{% load cache %}{% cache 10 long_cache_key poem %}Some Content{% endcache %}'})
    def test_cache17(self):
        """
        Regression test for #11270.
        """
        output = render('cache17', {'poem': 'Oh freddled gruntbuggly/'
                                            'Thy micturations are to me/'
                                            'As plurdled gabbleblotchits/'
                                            'On a lurgid bee/'
                                            'That mordiously hath bitled out/'
                                            'Its earted jurtles/'
                                            'Into a rancid festering/'
                                            'Or else I shall rend thee in the gobberwarts'
                                            'with my blurglecruncheon/'
                                            'See if I dont.'})
        self.assertEqual(output, 'Some Content')

    @setup({'cache18': '{% load cache custom %}{% cache 2|noop:"x y" cache18 %}cache18{% endcache %}'})
    def test_cache18(self):
        """
        Test whitespace in filter arguments
        """
        output = render('cache18')
        self.assertEqual(output, 'cache18')
