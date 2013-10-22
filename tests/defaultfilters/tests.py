# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import decimal

from django.template.defaultfilters import *
from django.test import TestCase
from django.test.utils import TransRealMixin
from django.utils import six
from django.utils import unittest, translation
from django.utils.safestring import SafeData
from django.utils.encoding import python_2_unicode_compatible


class DefaultFiltersTests(TestCase):

    def test_floatformat(self):
        self.assertEqual(floatformat(7.7), '7.7')
        self.assertEqual(floatformat(7.0), '7')
        self.assertEqual(floatformat(0.7), '0.7')
        self.assertEqual(floatformat(0.07), '0.1')
        self.assertEqual(floatformat(0.007), '0.0')
        self.assertEqual(floatformat(0.0), '0')
        self.assertEqual(floatformat(7.7, 3), '7.700')
        self.assertEqual(floatformat(6.000000, 3), '6.000')
        self.assertEqual(floatformat(6.200000, 3), '6.200')
        self.assertEqual(floatformat(6.200000, -3), '6.200')
        self.assertEqual(floatformat(13.1031, -3), '13.103')
        self.assertEqual(floatformat(11.1197, -2), '11.12')
        self.assertEqual(floatformat(11.0000, -2), '11')
        self.assertEqual(floatformat(11.000001, -2), '11.00')
        self.assertEqual(floatformat(8.2798, 3), '8.280')
        self.assertEqual(floatformat(5555.555, 2), '5555.56')
        self.assertEqual(floatformat(001.3000, 2), '1.30')
        self.assertEqual(floatformat(0.12345, 2), '0.12')
        self.assertEqual(floatformat(decimal.Decimal('555.555'), 2), '555.56')
        self.assertEqual(floatformat(decimal.Decimal('09.000')), '9')
        self.assertEqual(floatformat('foo'), '')
        self.assertEqual(floatformat(13.1031, 'bar'), '13.1031')
        self.assertEqual(floatformat(18.125, 2), '18.13')
        self.assertEqual(floatformat('foo', 'bar'), '')
        self.assertEqual(floatformat('¿Cómo esta usted?'), '')
        self.assertEqual(floatformat(None), '')

        # Check that we're not converting to scientific notation.
        self.assertEqual(floatformat(0, 6), '0.000000')
        self.assertEqual(floatformat(0, 7), '0.0000000')
        self.assertEqual(floatformat(0, 10), '0.0000000000')
        self.assertEqual(floatformat(0.000000000000000000015, 20),
                                     '0.00000000000000000002')

        pos_inf = float(1e30000)
        self.assertEqual(floatformat(pos_inf), six.text_type(pos_inf))

        neg_inf = float(-1e30000)
        self.assertEqual(floatformat(neg_inf), six.text_type(neg_inf))

        nan = pos_inf / pos_inf
        self.assertEqual(floatformat(nan), six.text_type(nan))

        class FloatWrapper(object):
            def __init__(self, value):
                self.value = value
            def __float__(self):
                return self.value

        self.assertEqual(floatformat(FloatWrapper(11.000001), -2), '11.00')

        # Regression for #15789
        decimal_ctx = decimal.getcontext()
        old_prec, decimal_ctx.prec = decimal_ctx.prec, 2
        try:
            self.assertEqual(floatformat(1.2345, 2), '1.23')
            self.assertEqual(floatformat(15.2042, -3), '15.204')
            self.assertEqual(floatformat(1.2345, '2'), '1.23')
            self.assertEqual(floatformat(15.2042, '-3'), '15.204')
            self.assertEqual(floatformat(decimal.Decimal('1.2345'), 2), '1.23')
            self.assertEqual(floatformat(decimal.Decimal('15.2042'), -3), '15.204')
        finally:
            decimal_ctx.prec = old_prec


    def test_floatformat_py2_fail(self):
        self.assertEqual(floatformat(1.00000000000000015, 16), '1.0000000000000002')

    # The test above fails because of Python 2's float handling. Floats with
    # many zeroes after the decimal point should be passed in as another type
    # such as unicode or Decimal.
    if six.PY2:
        test_floatformat_py2_fail = unittest.expectedFailure(test_floatformat_py2_fail)


    def test_addslashes(self):
        self.assertEqual(addslashes('"double quotes" and \'single quotes\''),
                          '\\"double quotes\\" and \\\'single quotes\\\'')

        self.assertEqual(addslashes(r'\ : backslashes, too'),
                          '\\\\ : backslashes, too')

    def test_capfirst(self):
        self.assertEqual(capfirst('hello world'), 'Hello world')

    def test_escapejs(self):
        self.assertEqual(escapejs_filter('"double quotes" and \'single quotes\''),
            '\\u0022double quotes\\u0022 and \\u0027single quotes\\u0027')
        self.assertEqual(escapejs_filter(r'\ : backslashes, too'),
            '\\u005C : backslashes, too')
        self.assertEqual(escapejs_filter('and lots of whitespace: \r\n\t\v\f\b'),
            'and lots of whitespace: \\u000D\\u000A\\u0009\\u000B\\u000C\\u0008')
        self.assertEqual(escapejs_filter(r'<script>and this</script>'),
            '\\u003Cscript\\u003Eand this\\u003C/script\\u003E')
        self.assertEqual(
            escapejs_filter('paragraph separator:\u2029and line separator:\u2028'),
            'paragraph separator:\\u2029and line separator:\\u2028')

    def test_fix_ampersands(self):
        self.assertEqual(fix_ampersands_filter('Jack & Jill & Jeroboam'),
                          'Jack &amp; Jill &amp; Jeroboam')

    def test_linenumbers(self):
        self.assertEqual(linenumbers('line 1\nline 2'),
                          '1. line 1\n2. line 2')
        self.assertEqual(linenumbers('\n'.join(['x'] * 10)),
                          '01. x\n02. x\n03. x\n04. x\n05. x\n06. x\n07. '\
                          'x\n08. x\n09. x\n10. x')

    def test_lower(self):
        self.assertEqual(lower('TEST'), 'test')

        # uppercase E umlaut
        self.assertEqual(lower('\xcb'), '\xeb')

    def test_make_list(self):
        self.assertEqual(make_list('abc'), ['a', 'b', 'c'])
        self.assertEqual(make_list(1234), ['1', '2', '3', '4'])

    def test_slugify(self):
        self.assertEqual(slugify(' Jack & Jill like numbers 1,2,3 and 4 and'\
            ' silly characters ?%.$!/'),
            'jack-jill-like-numbers-123-and-4-and-silly-characters')

        self.assertEqual(slugify("Un \xe9l\xe9phant \xe0 l'or\xe9e du bois"),
                          'un-elephant-a-loree-du-bois')

    def test_stringformat(self):
        self.assertEqual(stringformat(1, '03d'), '001')
        self.assertEqual(stringformat(1, 'z'), '')

    def test_title(self):
        self.assertEqual(title('a nice title, isn\'t it?'),
                          "A Nice Title, Isn't It?")
        self.assertEqual(title('discoth\xe8que'), 'Discoth\xe8que')

    def test_truncatewords(self):
        self.assertEqual(
            truncatewords('A sentence with a few words in it', 1), 'A ...')
        self.assertEqual(
            truncatewords('A sentence with a few words in it', 5),
            'A sentence with a few ...')
        self.assertEqual(
            truncatewords('A sentence with a few words in it', 100),
            'A sentence with a few words in it')
        self.assertEqual(
            truncatewords('A sentence with a few words in it',
            'not a number'), 'A sentence with a few words in it')

    def test_truncatewords_html(self):
        self.assertEqual(truncatewords_html(
            '<p>one <a href="#">two - three <br>four</a> five</p>', 0), '')
        self.assertEqual(truncatewords_html('<p>one <a href="#">two - '\
            'three <br>four</a> five</p>', 2),
            '<p>one <a href="#">two ...</a></p>')
        self.assertEqual(truncatewords_html(
            '<p>one <a href="#">two - three <br>four</a> five</p>', 4),
            '<p>one <a href="#">two - three <br>four ...</a></p>')
        self.assertEqual(truncatewords_html(
            '<p>one <a href="#">two - three <br>four</a> five</p>', 5),
            '<p>one <a href="#">two - three <br>four</a> five</p>')
        self.assertEqual(truncatewords_html(
            '<p>one <a href="#">two - three <br>four</a> five</p>', 100),
            '<p>one <a href="#">two - three <br>four</a> five</p>')
        self.assertEqual(truncatewords_html(
            '\xc5ngstr\xf6m was here', 1), '\xc5ngstr\xf6m ...')

    def test_upper(self):
        self.assertEqual(upper('Mixed case input'), 'MIXED CASE INPUT')
        # lowercase e umlaut
        self.assertEqual(upper('\xeb'), '\xcb')

    def test_urlencode(self):
        self.assertEqual(urlencode('fran\xe7ois & jill'),
                          'fran%C3%A7ois%20%26%20jill')
        self.assertEqual(urlencode(1), '1')

    def test_iriencode(self):
        self.assertEqual(iriencode('S\xf8r-Tr\xf8ndelag'),
                          'S%C3%B8r-Tr%C3%B8ndelag')
        self.assertEqual(iriencode(urlencode('fran\xe7ois & jill')),
                          'fran%C3%A7ois%20%26%20jill')

    def test_urlizetrunc(self):
        self.assertEqual(urlizetrunc('http://short.com/', 20), '<a href='\
            '"http://short.com/" rel="nofollow">http://short.com/</a>')

        self.assertEqual(urlizetrunc('http://www.google.co.uk/search?hl=en'\
            '&q=some+long+url&btnG=Search&meta=', 20), '<a href="http://'\
            'www.google.co.uk/search?hl=en&q=some+long+url&btnG=Search&'\
            'meta=" rel="nofollow">http://www.google...</a>')

        self.assertEqual(urlizetrunc('http://www.google.co.uk/search?hl=en'\
            '&q=some+long+url&btnG=Search&meta=', 20), '<a href="http://'\
            'www.google.co.uk/search?hl=en&q=some+long+url&btnG=Search'\
            '&meta=" rel="nofollow">http://www.google...</a>')

        # Check truncating of URIs which are the exact length
        uri = 'http://31characteruri.com/test/'
        self.assertEqual(len(uri), 31)

        self.assertEqual(urlizetrunc(uri, 31),
            '<a href="http://31characteruri.com/test/" rel="nofollow">'\
            'http://31characteruri.com/test/</a>')

        self.assertEqual(urlizetrunc(uri, 30),
            '<a href="http://31characteruri.com/test/" rel="nofollow">'\
            'http://31characteruri.com/t...</a>')

        self.assertEqual(urlizetrunc(uri, 2),
            '<a href="http://31characteruri.com/test/"'\
            ' rel="nofollow">...</a>')

    def test_urlize(self):
        # Check normal urlize
        self.assertEqual(urlize('http://google.com'),
            '<a href="http://google.com" rel="nofollow">http://google.com</a>')
        self.assertEqual(urlize('http://google.com/'),
            '<a href="http://google.com/" rel="nofollow">http://google.com/</a>')
        self.assertEqual(urlize('www.google.com'),
            '<a href="http://www.google.com" rel="nofollow">www.google.com</a>')
        self.assertEqual(urlize('djangoproject.org'),
            '<a href="http://djangoproject.org" rel="nofollow">djangoproject.org</a>')
        self.assertEqual(urlize('info@djangoproject.org'),
            '<a href="mailto:info@djangoproject.org">info@djangoproject.org</a>')

        # Check urlize with https addresses
        self.assertEqual(urlize('https://google.com'),
            '<a href="https://google.com" rel="nofollow">https://google.com</a>')

        # Check urlize doesn't overquote already quoted urls - see #9655
        # The teststring is the urlquoted version of 'http://hi.baidu.com/重新开始'
        self.assertEqual(urlize('http://hi.baidu.com/%E9%87%8D%E6%96%B0%E5%BC%80%E5%A7%8B'),
            '<a href="http://hi.baidu.com/%E9%87%8D%E6%96%B0%E5%BC%80%E5%A7%8B" rel="nofollow">'
            'http://hi.baidu.com/%E9%87%8D%E6%96%B0%E5%BC%80%E5%A7%8B</a>')
        self.assertEqual(urlize('www.mystore.com/30%OffCoupons!'),
            '<a href="http://www.mystore.com/30%25OffCoupons!" rel="nofollow">'
            'www.mystore.com/30%OffCoupons!</a>')
        self.assertEqual(urlize('http://en.wikipedia.org/wiki/Caf%C3%A9'),
            '<a href="http://en.wikipedia.org/wiki/Caf%C3%A9" rel="nofollow">'
            'http://en.wikipedia.org/wiki/Caf%C3%A9</a>')
        self.assertEqual(urlize('http://en.wikipedia.org/wiki/Café'),
            '<a href="http://en.wikipedia.org/wiki/Caf%C3%A9" rel="nofollow">'
            'http://en.wikipedia.org/wiki/Café</a>')

        # Check urlize keeps balanced parentheses - see #11911
        self.assertEqual(urlize('http://en.wikipedia.org/wiki/Django_(web_framework)'),
            '<a href="http://en.wikipedia.org/wiki/Django_(web_framework)" rel="nofollow">'
            'http://en.wikipedia.org/wiki/Django_(web_framework)</a>')
        self.assertEqual(urlize('(see http://en.wikipedia.org/wiki/Django_(web_framework))'),
            '(see <a href="http://en.wikipedia.org/wiki/Django_(web_framework)" rel="nofollow">'
            'http://en.wikipedia.org/wiki/Django_(web_framework)</a>)')

        # Check urlize adds nofollow properly - see #12183
        self.assertEqual(urlize('foo@bar.com or www.bar.com'),
            '<a href="mailto:foo@bar.com">foo@bar.com</a> or '
            '<a href="http://www.bar.com" rel="nofollow">www.bar.com</a>')

        # Check urlize handles IDN correctly - see #13704
        self.assertEqual(urlize('http://c✶.ws'),
            '<a href="http://xn--c-lgq.ws" rel="nofollow">http://c✶.ws</a>')
        self.assertEqual(urlize('www.c✶.ws'),
            '<a href="http://www.xn--c-lgq.ws" rel="nofollow">www.c✶.ws</a>')
        self.assertEqual(urlize('c✶.org'),
            '<a href="http://xn--c-lgq.org" rel="nofollow">c✶.org</a>')
        self.assertEqual(urlize('info@c✶.org'),
            '<a href="mailto:info@xn--c-lgq.org">info@c✶.org</a>')

        # Check urlize doesn't highlight malformed URIs - see #16395
        self.assertEqual(urlize('http:///www.google.com'),
           'http:///www.google.com')
        self.assertEqual(urlize('http://.google.com'),
            'http://.google.com')
        self.assertEqual(urlize('http://@foo.com'),
            'http://@foo.com')

        # Check urlize accepts more TLDs - see #16656
        self.assertEqual(urlize('usa.gov'),
            '<a href="http://usa.gov" rel="nofollow">usa.gov</a>')

        # Check urlize don't crash on invalid email with dot-starting domain - see #17592
        self.assertEqual(urlize('email@.stream.ru'),
            'email@.stream.ru')

        # Check urlize accepts uppercased URL schemes - see #18071
        self.assertEqual(urlize('HTTPS://github.com/'),
            '<a href="https://github.com/" rel="nofollow">HTTPS://github.com/</a>')

        # Check urlize trims trailing period when followed by parenthesis - see #18644
        self.assertEqual(urlize('(Go to http://www.example.com/foo.)'),
            '(Go to <a href="http://www.example.com/foo" rel="nofollow">http://www.example.com/foo</a>.)')

        # Check urlize handles brackets properly (#19070)
        self.assertEqual(urlize('[see www.example.com]'),
            '[see <a href="http://www.example.com" rel="nofollow">www.example.com</a>]' )
        self.assertEqual(urlize('see test[at[example.com'),
            'see <a href="http://test[at[example.com" rel="nofollow">test[at[example.com</a>' )
        self.assertEqual(urlize('[http://168.192.0.1](http://168.192.0.1)'),
            '[<a href="http://168.192.0.1](http://168.192.0.1)" rel="nofollow">http://168.192.0.1](http://168.192.0.1)</a>')

        # Check urlize works with IPv4/IPv6 addresses
        self.assertEqual(urlize('http://192.168.0.15/api/9'),
            '<a href="http://192.168.0.15/api/9" rel="nofollow">http://192.168.0.15/api/9</a>')
        self.assertEqual(urlize('http://[2001:db8:cafe::2]/api/9'),
            '<a href="http://[2001:db8:cafe::2]/api/9" rel="nofollow">http://[2001:db8:cafe::2]/api/9</a>')

    def test_wordcount(self):
        self.assertEqual(wordcount(''), 0)
        self.assertEqual(wordcount('oneword'), 1)
        self.assertEqual(wordcount('lots of words'), 3)

        self.assertEqual(wordwrap('this is a long paragraph of text that '\
            'really needs to be wrapped I\'m afraid', 14),
            "this is a long\nparagraph of\ntext that\nreally needs\nto be "\
            "wrapped\nI'm afraid")

        self.assertEqual(wordwrap('this is a short paragraph of text.\n  '\
            'But this line should be indented', 14),
            'this is a\nshort\nparagraph of\ntext.\n  But this\nline '\
            'should be\nindented')

        self.assertEqual(wordwrap('this is a short paragraph of text.\n  '\
            'But this line should be indented',15), 'this is a short\n'\
            'paragraph of\ntext.\n  But this line\nshould be\nindented')

    def test_rjust(self):
        self.assertEqual(ljust('test', 10), 'test      ')
        self.assertEqual(ljust('test', 3), 'test')
        self.assertEqual(rjust('test', 10), '      test')
        self.assertEqual(rjust('test', 3), 'test')

    def test_center(self):
        self.assertEqual(center('test', 6), ' test ')

    def test_cut(self):
        self.assertEqual(cut('a string to be mangled', 'a'),
                          ' string to be mngled')
        self.assertEqual(cut('a string to be mangled', 'ng'),
                          'a stri to be maled')
        self.assertEqual(cut('a string to be mangled', 'strings'),
                          'a string to be mangled')

    def test_force_escape(self):
        escaped = force_escape('<some html & special characters > here')
        self.assertEqual(
            escaped, '&lt;some html &amp; special characters &gt; here')
        self.assertIsInstance(escaped, SafeData)
        self.assertEqual(
            force_escape('<some html & special characters > here ĐÅ€£'),
            '&lt;some html &amp; special characters &gt; here'\
            ' \u0110\xc5\u20ac\xa3')

    def test_linebreaks(self):
        self.assertEqual(linebreaks_filter('line 1'), '<p>line 1</p>')
        self.assertEqual(linebreaks_filter('line 1\nline 2'),
                          '<p>line 1<br />line 2</p>')
        self.assertEqual(linebreaks_filter('line 1\rline 2'),
                          '<p>line 1<br />line 2</p>')
        self.assertEqual(linebreaks_filter('line 1\r\nline 2'),
                          '<p>line 1<br />line 2</p>')

    def test_linebreaksbr(self):
        self.assertEqual(linebreaksbr('line 1\nline 2'),
                          'line 1<br />line 2')
        self.assertEqual(linebreaksbr('line 1\rline 2'),
                          'line 1<br />line 2')
        self.assertEqual(linebreaksbr('line 1\r\nline 2'),
                          'line 1<br />line 2')

    def test_removetags(self):
        self.assertEqual(removetags('some <b>html</b> with <script>alert'\
            '("You smell")</script> disallowed <img /> tags', 'script img'),
            'some <b>html</b> with alert("You smell") disallowed  tags')
        self.assertEqual(striptags('some <b>html</b> with <script>alert'\
            '("You smell")</script> disallowed <img /> tags'),
            'some html with alert("You smell") disallowed  tags')

    def test_dictsort(self):
        sorted_dicts = dictsort([{'age': 23, 'name': 'Barbara-Ann'},
                                 {'age': 63, 'name': 'Ra Ra Rasputin'},
                                 {'name': 'Jonny B Goode', 'age': 18}], 'age')

        self.assertEqual([sorted(dict.items()) for dict in sorted_dicts],
            [[('age', 18), ('name', 'Jonny B Goode')],
             [('age', 23), ('name', 'Barbara-Ann')],
             [('age', 63), ('name', 'Ra Ra Rasputin')]])

        # If it gets passed a list of something else different from
        # dictionaries it should fail silently
        self.assertEqual(dictsort([1, 2, 3], 'age'), '')
        self.assertEqual(dictsort('Hello!', 'age'), '')
        self.assertEqual(dictsort({'a': 1}, 'age'), '')
        self.assertEqual(dictsort(1, 'age'), '')

    def test_dictsortreversed(self):
        sorted_dicts = dictsortreversed([{'age': 23, 'name': 'Barbara-Ann'},
                                         {'age': 63, 'name': 'Ra Ra Rasputin'},
                                         {'name': 'Jonny B Goode', 'age': 18}],
                                        'age')

        self.assertEqual([sorted(dict.items()) for dict in sorted_dicts],
            [[('age', 63), ('name', 'Ra Ra Rasputin')],
             [('age', 23), ('name', 'Barbara-Ann')],
             [('age', 18), ('name', 'Jonny B Goode')]])

        # If it gets passed a list of something else different from
        # dictionaries it should fail silently
        self.assertEqual(dictsortreversed([1, 2, 3], 'age'), '')
        self.assertEqual(dictsortreversed('Hello!', 'age'), '')
        self.assertEqual(dictsortreversed({'a': 1}, 'age'), '')
        self.assertEqual(dictsortreversed(1, 'age'), '')

    def test_first(self):
        self.assertEqual(first([0,1,2]), 0)
        self.assertEqual(first(''), '')
        self.assertEqual(first('test'), 't')

    def test_join(self):
        self.assertEqual(join([0,1,2], 'glue'), '0glue1glue2')

    def test_length(self):
        self.assertEqual(length('1234'), 4)
        self.assertEqual(length([1,2,3,4]), 4)
        self.assertEqual(length_is([], 0), True)
        self.assertEqual(length_is([], 1), False)
        self.assertEqual(length_is('a', 1), True)
        self.assertEqual(length_is('a', 10), False)

    def test_slice(self):
        self.assertEqual(slice_filter('abcdefg', '0'), '')
        self.assertEqual(slice_filter('abcdefg', '1'), 'a')
        self.assertEqual(slice_filter('abcdefg', '-1'), 'abcdef')
        self.assertEqual(slice_filter('abcdefg', '1:2'), 'b')
        self.assertEqual(slice_filter('abcdefg', '1:3'), 'bc')
        self.assertEqual(slice_filter('abcdefg', '0::2'), 'aceg')

    def test_unordered_list(self):
        self.assertEqual(unordered_list(['item 1', 'item 2']),
            '\t<li>item 1</li>\n\t<li>item 2</li>')
        self.assertEqual(unordered_list(['item 1', ['item 1.1']]),
            '\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1</li>\n\t</ul>\n\t</li>')

        self.assertEqual(
            unordered_list(['item 1', ['item 1.1', 'item1.2'], 'item 2']),
            '\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1</li>\n\t\t<li>item1.2'\
            '</li>\n\t</ul>\n\t</li>\n\t<li>item 2</li>')

        self.assertEqual(
            unordered_list(['item 1', ['item 1.1', ['item 1.1.1',
                                                      ['item 1.1.1.1']]]]),
            '\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1\n\t\t<ul>\n\t\t\t<li>'\
            'item 1.1.1\n\t\t\t<ul>\n\t\t\t\t<li>item 1.1.1.1</li>\n\t\t\t'\
            '</ul>\n\t\t\t</li>\n\t\t</ul>\n\t\t</li>\n\t</ul>\n\t</li>')

        self.assertEqual(unordered_list(
            ['States', ['Kansas', ['Lawrence', 'Topeka'], 'Illinois']]),
            '\t<li>States\n\t<ul>\n\t\t<li>Kansas\n\t\t<ul>\n\t\t\t<li>'\
            'Lawrence</li>\n\t\t\t<li>Topeka</li>\n\t\t</ul>\n\t\t</li>'\
            '\n\t\t<li>Illinois</li>\n\t</ul>\n\t</li>')

        @python_2_unicode_compatible
        class ULItem(object):
            def __init__(self, title):
              self.title = title
            def __str__(self):
                return 'ulitem-%s' % str(self.title)

        a = ULItem('a')
        b = ULItem('b')
        self.assertEqual(unordered_list([a,b]),
                          '\t<li>ulitem-a</li>\n\t<li>ulitem-b</li>')

        # Old format for unordered lists should still work
        self.assertEqual(unordered_list(['item 1', []]), '\t<li>item 1</li>')

        self.assertEqual(unordered_list(['item 1', [['item 1.1', []]]]),
            '\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1</li>\n\t</ul>\n\t</li>')

        self.assertEqual(unordered_list(['item 1', [['item 1.1', []],
            ['item 1.2', []]]]), '\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1'\
            '</li>\n\t\t<li>item 1.2</li>\n\t</ul>\n\t</li>')

        self.assertEqual(unordered_list(['States', [['Kansas', [['Lawrence',
            []], ['Topeka', []]]], ['Illinois', []]]]), '\t<li>States\n\t'\
            '<ul>\n\t\t<li>Kansas\n\t\t<ul>\n\t\t\t<li>Lawrence</li>'\
            '\n\t\t\t<li>Topeka</li>\n\t\t</ul>\n\t\t</li>\n\t\t<li>'\
            'Illinois</li>\n\t</ul>\n\t</li>')

    def test_add(self):
        self.assertEqual(add('1', '2'), 3)

    def test_get_digit(self):
        self.assertEqual(get_digit(123, 1), 3)
        self.assertEqual(get_digit(123, 2), 2)
        self.assertEqual(get_digit(123, 3), 1)
        self.assertEqual(get_digit(123, 4), 0)
        self.assertEqual(get_digit(123, 0), 123)
        self.assertEqual(get_digit('xyz', 0), 'xyz')

    def test_date(self):
        # real testing of date() is in dateformat.py
        self.assertEqual(date(datetime.datetime(2005, 12, 29), "d F Y"),
                          '29 December 2005')
        self.assertEqual(date(datetime.datetime(2005, 12, 29), r'jS \o\f F'),
                          '29th of December')

    def test_time(self):
        # real testing of time() is done in dateformat.py
        self.assertEqual(time(datetime.time(13), "h"), '01')
        self.assertEqual(time(datetime.time(0), "h"), '12')

    def test_timesince(self):
        # real testing is done in timesince.py, where we can provide our own 'now'
        # NOTE: \xa0 avoids wrapping between value and unit
        self.assertEqual(
            timesince_filter(datetime.datetime.now() - datetime.timedelta(1)),
            '1\xa0day')

        self.assertEqual(
            timesince_filter(datetime.datetime(2005, 12, 29),
                             datetime.datetime(2005, 12, 30)),
            '1\xa0day')

    def test_timeuntil(self):
        # NOTE: \xa0 avoids wrapping between value and unit
        self.assertEqual(
            timeuntil_filter(datetime.datetime.now() + datetime.timedelta(1, 1)),
            '1\xa0day')

        self.assertEqual(
            timeuntil_filter(datetime.datetime(2005, 12, 30),
                             datetime.datetime(2005, 12, 29)),
            '1\xa0day')

    def test_default(self):
        self.assertEqual(default("val", "default"), 'val')
        self.assertEqual(default(None, "default"), 'default')
        self.assertEqual(default('', "default"), 'default')

    def test_if_none(self):
        self.assertEqual(default_if_none("val", "default"), 'val')
        self.assertEqual(default_if_none(None, "default"), 'default')
        self.assertEqual(default_if_none('', "default"), '')

    def test_divisibleby(self):
        self.assertEqual(divisibleby(4, 2), True)
        self.assertEqual(divisibleby(4, 3), False)

    def test_yesno(self):
        self.assertEqual(yesno(True), 'yes')
        self.assertEqual(yesno(False), 'no')
        self.assertEqual(yesno(None), 'maybe')
        self.assertEqual(yesno(True, 'certainly,get out of town,perhaps'),
                          'certainly')
        self.assertEqual(yesno(False, 'certainly,get out of town,perhaps'),
                          'get out of town')
        self.assertEqual(yesno(None, 'certainly,get out of town,perhaps'),
                          'perhaps')
        self.assertEqual(yesno(None, 'certainly,get out of town'),
                          'get out of town')

    def test_filesizeformat(self):
        # NOTE: \xa0 avoids wrapping between value and unit
        self.assertEqual(filesizeformat(1023), '1023\xa0bytes')
        self.assertEqual(filesizeformat(1024), '1.0\xa0KB')
        self.assertEqual(filesizeformat(10*1024), '10.0\xa0KB')
        self.assertEqual(filesizeformat(1024*1024-1), '1024.0\xa0KB')
        self.assertEqual(filesizeformat(1024*1024), '1.0\xa0MB')
        self.assertEqual(filesizeformat(1024*1024*50), '50.0\xa0MB')
        self.assertEqual(filesizeformat(1024*1024*1024-1), '1024.0\xa0MB')
        self.assertEqual(filesizeformat(1024*1024*1024), '1.0\xa0GB')
        self.assertEqual(filesizeformat(1024*1024*1024*1024), '1.0\xa0TB')
        self.assertEqual(filesizeformat(1024*1024*1024*1024*1024), '1.0\xa0PB')
        self.assertEqual(filesizeformat(1024*1024*1024*1024*1024*2000),
                          '2000.0\xa0PB')
        self.assertEqual(filesizeformat(complex(1,-1)), '0\xa0bytes')
        self.assertEqual(filesizeformat(""), '0\xa0bytes')
        self.assertEqual(filesizeformat("\N{GREEK SMALL LETTER ALPHA}"),
                          '0\xa0bytes')

    def test_pluralize(self):
        self.assertEqual(pluralize(1), '')
        self.assertEqual(pluralize(0), 's')
        self.assertEqual(pluralize(2), 's')
        self.assertEqual(pluralize([1]), '')
        self.assertEqual(pluralize([]), 's')
        self.assertEqual(pluralize([1,2,3]), 's')
        self.assertEqual(pluralize(1,'es'), '')
        self.assertEqual(pluralize(0,'es'), 'es')
        self.assertEqual(pluralize(2,'es'), 'es')
        self.assertEqual(pluralize(1,'y,ies'), 'y')
        self.assertEqual(pluralize(0,'y,ies'), 'ies')
        self.assertEqual(pluralize(2,'y,ies'), 'ies')
        self.assertEqual(pluralize(0,'y,ies,error'), '')

    def test_phone2numeric(self):
        self.assertEqual(phone2numeric_filter('0800 flowers'), '0800 3569377')

    def test_non_string_input(self):
        # Filters shouldn't break if passed non-strings
        self.assertEqual(addslashes(123), '123')
        self.assertEqual(linenumbers(123), '1. 123')
        self.assertEqual(lower(123), '123')
        self.assertEqual(make_list(123), ['1', '2', '3'])
        self.assertEqual(slugify(123), '123')
        self.assertEqual(title(123), '123')
        self.assertEqual(truncatewords(123, 2), '123')
        self.assertEqual(upper(123), '123')
        self.assertEqual(urlencode(123), '123')
        self.assertEqual(urlize(123), '123')
        self.assertEqual(urlizetrunc(123, 1), '123')
        self.assertEqual(wordcount(123), 1)
        self.assertEqual(wordwrap(123, 2), '123')
        self.assertEqual(ljust('123', 4), '123 ')
        self.assertEqual(rjust('123', 4), ' 123')
        self.assertEqual(center('123', 5), ' 123 ')
        self.assertEqual(center('123', 6), ' 123  ')
        self.assertEqual(cut(123, '2'), '13')
        self.assertEqual(escape(123), '123')
        self.assertEqual(linebreaks_filter(123), '<p>123</p>')
        self.assertEqual(linebreaksbr(123), '123')
        self.assertEqual(removetags(123, 'a'), '123')
        self.assertEqual(striptags(123), '123')


class DefaultFiltersI18NTests(TransRealMixin, TestCase):

    def test_localized_filesizeformat(self):
        # NOTE: \xa0 avoids wrapping between value and unit
        with self.settings(USE_L10N=True):
            with translation.override('de', deactivate=True):
                self.assertEqual(filesizeformat(1023), '1023\xa0Bytes')
                self.assertEqual(filesizeformat(1024), '1,0\xa0KB')
                self.assertEqual(filesizeformat(10*1024), '10,0\xa0KB')
                self.assertEqual(filesizeformat(1024*1024-1), '1024,0\xa0KB')
                self.assertEqual(filesizeformat(1024*1024), '1,0\xa0MB')
                self.assertEqual(filesizeformat(1024*1024*50), '50,0\xa0MB')
                self.assertEqual(filesizeformat(1024*1024*1024-1), '1024,0\xa0MB')
                self.assertEqual(filesizeformat(1024*1024*1024), '1,0\xa0GB')
                self.assertEqual(filesizeformat(1024*1024*1024*1024), '1,0\xa0TB')
                self.assertEqual(filesizeformat(1024*1024*1024*1024*1024),
                                  '1,0\xa0PB')
                self.assertEqual(filesizeformat(1024*1024*1024*1024*1024*2000),
                                  '2000,0\xa0PB')
                self.assertEqual(filesizeformat(complex(1,-1)), '0\xa0Bytes')
                self.assertEqual(filesizeformat(""), '0\xa0Bytes')
                self.assertEqual(filesizeformat("\N{GREEK SMALL LETTER ALPHA}"),
                                  '0\xa0Bytes')
