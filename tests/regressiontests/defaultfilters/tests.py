# -*- coding: utf-8 -*-
import datetime
import unittest

from django.template.defaultfilters import *

class DefaultFiltersTests(unittest.TestCase):

    def test_floatformat(self):
        self.assertEqual(floatformat(7.7), u'7.7')
        self.assertEqual(floatformat(7.0), u'7')
        self.assertEqual(floatformat(0.7), u'0.7')
        self.assertEqual(floatformat(0.07), u'0.1')
        self.assertEqual(floatformat(0.007), u'0.0')
        self.assertEqual(floatformat(0.0), u'0')
        self.assertEqual(floatformat(7.7, 3), u'7.700')
        self.assertEqual(floatformat(6.000000, 3), u'6.000')
        self.assertEqual(floatformat(6.200000, 3), u'6.200')
        self.assertEqual(floatformat(6.200000, -3), u'6.200')
        self.assertEqual(floatformat(13.1031, -3), u'13.103')
        self.assertEqual(floatformat(11.1197, -2), u'11.12')
        self.assertEqual(floatformat(11.0000, -2), u'11')
        self.assertEqual(floatformat(11.000001, -2), u'11.00')
        self.assertEqual(floatformat(8.2798, 3), u'8.280')
        self.assertEqual(floatformat(u'foo'), u'')
        self.assertEqual(floatformat(13.1031, u'bar'), u'13.1031')
        self.assertEqual(floatformat(18.125, 2), u'18.13')
        self.assertEqual(floatformat(u'foo', u'bar'), u'')
        self.assertEqual(floatformat(u'¿Cómo esta usted?'), u'')
        self.assertEqual(floatformat(None), u'')

        pos_inf = float(1e30000)
        self.assertEqual(floatformat(pos_inf), unicode(pos_inf))

        neg_inf = float(-1e30000)
        self.assertEqual(floatformat(neg_inf), unicode(neg_inf))

        nan = pos_inf / pos_inf
        self.assertEqual(floatformat(nan), unicode(nan))

        class FloatWrapper(object):
            def __init__(self, value):
                self.value = value
            def __float__(self):
                return self.value

        self.assertEqual(floatformat(FloatWrapper(11.000001), -2), u'11.00')

    def test_addslashes(self):
        self.assertEqual(addslashes(u'"double quotes" and \'single quotes\''),
                          u'\\"double quotes\\" and \\\'single quotes\\\'')

        self.assertEqual(addslashes(ur'\ : backslashes, too'),
                          u'\\\\ : backslashes, too')

    def test_capfirst(self):
        self.assertEqual(capfirst(u'hello world'), u'Hello world')

    def test_escapejs(self):
        self.assertEqual(escapejs(u'"double quotes" and \'single quotes\''),
            u'\\u0022double quotes\\u0022 and \\u0027single quotes\\u0027')
        self.assertEqual(escapejs(ur'\ : backslashes, too'),
            u'\\u005C : backslashes, too')
        self.assertEqual(escapejs(u'and lots of whitespace: \r\n\t\v\f\b'),
            u'and lots of whitespace: \\u000D\\u000A\\u0009\\u000B\\u000C\\u0008')
        self.assertEqual(escapejs(ur'<script>and this</script>'),
            u'\\u003Cscript\\u003Eand this\\u003C/script\\u003E')
        self.assertEqual(
            escapejs(u'paragraph separator:\u2029and line separator:\u2028'),
            u'paragraph separator:\\u2029and line separator:\\u2028')

    def test_fix_ampersands(self):
        self.assertEqual(fix_ampersands(u'Jack & Jill & Jeroboam'),
                          u'Jack &amp; Jill &amp; Jeroboam')

    def test_linenumbers(self):
        self.assertEqual(linenumbers(u'line 1\nline 2'),
                          u'1. line 1\n2. line 2')
        self.assertEqual(linenumbers(u'\n'.join([u'x'] * 10)),
                          u'01. x\n02. x\n03. x\n04. x\n05. x\n06. x\n07. '\
                          u'x\n08. x\n09. x\n10. x')

    def test_lower(self):
        self.assertEqual(lower('TEST'), u'test')

        # uppercase E umlaut
        self.assertEqual(lower(u'\xcb'), u'\xeb')

    def test_make_list(self):
        self.assertEqual(make_list('abc'), [u'a', u'b', u'c'])
        self.assertEqual(make_list(1234), [u'1', u'2', u'3', u'4'])

    def test_slugify(self):
        self.assertEqual(slugify(' Jack & Jill like numbers 1,2,3 and 4 and'\
            ' silly characters ?%.$!/'),
            u'jack-jill-like-numbers-123-and-4-and-silly-characters')

        self.assertEqual(slugify(u"Un \xe9l\xe9phant \xe0 l'or\xe9e du bois"),
                          u'un-elephant-a-loree-du-bois')

    def test_stringformat(self):
        self.assertEqual(stringformat(1, u'03d'), u'001')
        self.assertEqual(stringformat(1, u'z'), u'')

    def test_title(self):
        self.assertEqual(title('a nice title, isn\'t it?'),
                          u"A Nice Title, Isn't It?")
        self.assertEqual(title(u'discoth\xe8que'), u'Discoth\xe8que')

    def test_truncatewords(self):
        self.assertEqual(
            truncatewords(u'A sentence with a few words in it', 1), u'A ...')
        self.assertEqual(
            truncatewords(u'A sentence with a few words in it', 5),
            u'A sentence with a few ...')
        self.assertEqual(
            truncatewords(u'A sentence with a few words in it', 100),
            u'A sentence with a few words in it')
        self.assertEqual(
            truncatewords(u'A sentence with a few words in it',
            'not a number'), u'A sentence with a few words in it')

    def test_truncatewords_html(self):
        self.assertEqual(truncatewords_html(
            u'<p>one <a href="#">two - three <br>four</a> five</p>', 0), u'')
        self.assertEqual(truncatewords_html(u'<p>one <a href="#">two - '\
            u'three <br>four</a> five</p>', 2),
            u'<p>one <a href="#">two ...</a></p>')
        self.assertEqual(truncatewords_html(
            u'<p>one <a href="#">two - three <br>four</a> five</p>', 4),
            u'<p>one <a href="#">two - three <br>four ...</a></p>')
        self.assertEqual(truncatewords_html(
            u'<p>one <a href="#">two - three <br>four</a> five</p>', 5),
            u'<p>one <a href="#">two - three <br>four</a> five</p>')
        self.assertEqual(truncatewords_html(
            u'<p>one <a href="#">two - three <br>four</a> five</p>', 100),
            u'<p>one <a href="#">two - three <br>four</a> five</p>')
        self.assertEqual(truncatewords_html(
            u'\xc5ngstr\xf6m was here', 1), u'\xc5ngstr\xf6m ...')

    def test_upper(self):
        self.assertEqual(upper(u'Mixed case input'), u'MIXED CASE INPUT')
        # lowercase e umlaut
        self.assertEqual(upper(u'\xeb'), u'\xcb')

    def test_urlencode(self):
        self.assertEqual(urlencode(u'fran\xe7ois & jill'),
                          u'fran%C3%A7ois%20%26%20jill')
        self.assertEqual(urlencode(1), u'1')

    def test_iriencode(self):
        self.assertEqual(iriencode(u'S\xf8r-Tr\xf8ndelag'),
                          u'S%C3%B8r-Tr%C3%B8ndelag')
        self.assertEqual(iriencode(urlencode(u'fran\xe7ois & jill')),
                          u'fran%C3%A7ois%20%26%20jill')

    def test_urlizetrunc(self):
        self.assertEqual(urlizetrunc(u'http://short.com/', 20), u'<a href='\
            u'"http://short.com/" rel="nofollow">http://short.com/</a>')

        self.assertEqual(urlizetrunc(u'http://www.google.co.uk/search?hl=en'\
            u'&q=some+long+url&btnG=Search&meta=', 20), u'<a href="http://'\
            u'www.google.co.uk/search?hl=en&q=some+long+url&btnG=Search&'\
            u'meta=" rel="nofollow">http://www.google...</a>')

        self.assertEqual(urlizetrunc('http://www.google.co.uk/search?hl=en'\
            u'&q=some+long+url&btnG=Search&meta=', 20), u'<a href="http://'\
            u'www.google.co.uk/search?hl=en&q=some+long+url&btnG=Search'\
            u'&meta=" rel="nofollow">http://www.google...</a>')

        # Check truncating of URIs which are the exact length
        uri = 'http://31characteruri.com/test/'
        self.assertEqual(len(uri), 31)

        self.assertEqual(urlizetrunc(uri, 31),
            u'<a href="http://31characteruri.com/test/" rel="nofollow">'\
            u'http://31characteruri.com/test/</a>')

        self.assertEqual(urlizetrunc(uri, 30),
            u'<a href="http://31characteruri.com/test/" rel="nofollow">'\
            u'http://31characteruri.com/t...</a>')

        self.assertEqual(urlizetrunc(uri, 2),
            u'<a href="http://31characteruri.com/test/"'\
            u' rel="nofollow">...</a>')

    def test_urlize(self):
        # Check normal urlize
        self.assertEqual(urlize('http://google.com'),
            u'<a href="http://google.com" rel="nofollow">http://google.com</a>')
        self.assertEqual(urlize('http://google.com/'),
            u'<a href="http://google.com/" rel="nofollow">http://google.com/</a>')
        self.assertEqual(urlize('www.google.com'),
            u'<a href="http://www.google.com" rel="nofollow">www.google.com</a>')
        self.assertEqual(urlize('djangoproject.org'),
            u'<a href="http://djangoproject.org" rel="nofollow">djangoproject.org</a>')
        self.assertEqual(urlize('info@djangoproject.org'),
            u'<a href="mailto:info@djangoproject.org">info@djangoproject.org</a>')

        # Check urlize with https addresses
        self.assertEqual(urlize('https://google.com'),
            u'<a href="https://google.com" rel="nofollow">https://google.com</a>')

    def test_wordcount(self):
        self.assertEqual(wordcount(''), 0)
        self.assertEqual(wordcount(u'oneword'), 1)
        self.assertEqual(wordcount(u'lots of words'), 3)

        self.assertEqual(wordwrap(u'this is a long paragraph of text that '\
            u'really needs to be wrapped I\'m afraid', 14),
            u"this is a long\nparagraph of\ntext that\nreally needs\nto be "\
            u"wrapped\nI'm afraid")

        self.assertEqual(wordwrap(u'this is a short paragraph of text.\n  '\
            u'But this line should be indented', 14),
            u'this is a\nshort\nparagraph of\ntext.\n  But this\nline '\
            u'should be\nindented')

        self.assertEqual(wordwrap(u'this is a short paragraph of text.\n  '\
            u'But this line should be indented',15), u'this is a short\n'\
            u'paragraph of\ntext.\n  But this line\nshould be\nindented')

    def test_rjust(self):
        self.assertEqual(ljust(u'test', 10), u'test      ')
        self.assertEqual(ljust(u'test', 3), u'test')
        self.assertEqual(rjust(u'test', 10), u'      test')
        self.assertEqual(rjust(u'test', 3), u'test')

    def test_center(self):
        self.assertEqual(center(u'test', 6), u' test ')

    def test_cut(self):
        self.assertEqual(cut(u'a string to be mangled', 'a'),
                          u' string to be mngled')
        self.assertEqual(cut(u'a string to be mangled', 'ng'),
                          u'a stri to be maled')
        self.assertEqual(cut(u'a string to be mangled', 'strings'),
                          u'a string to be mangled')

    def test_force_escape(self):
        self.assertEqual(
            force_escape(u'<some html & special characters > here'),
            u'&lt;some html &amp; special characters &gt; here')
        self.assertEqual(
            force_escape(u'<some html & special characters > here ĐÅ€£'),
            u'&lt;some html &amp; special characters &gt; here'\
            u' \u0110\xc5\u20ac\xa3')

    def test_linebreaks(self):
        self.assertEqual(linebreaks(u'line 1'), u'<p>line 1</p>')
        self.assertEqual(linebreaks(u'line 1\nline 2'),
                          u'<p>line 1<br />line 2</p>')

    def test_removetags(self):
        self.assertEqual(removetags(u'some <b>html</b> with <script>alert'\
            u'("You smell")</script> disallowed <img /> tags', 'script img'),
            u'some <b>html</b> with alert("You smell") disallowed  tags')
        self.assertEqual(striptags(u'some <b>html</b> with <script>alert'\
            u'("You smell")</script> disallowed <img /> tags'),
            u'some html with alert("You smell") disallowed  tags')

    def test_dictsort(self):
        sorted_dicts = dictsort([{'age': 23, 'name': 'Barbara-Ann'},
                                 {'age': 63, 'name': 'Ra Ra Rasputin'},
                                 {'name': 'Jonny B Goode', 'age': 18}], 'age')

        self.assertEqual([sorted(dict.items()) for dict in sorted_dicts],
            [[('age', 18), ('name', 'Jonny B Goode')],
             [('age', 23), ('name', 'Barbara-Ann')],
             [('age', 63), ('name', 'Ra Ra Rasputin')]])

    def test_dictsortreversed(self):
        sorted_dicts = dictsortreversed([{'age': 23, 'name': 'Barbara-Ann'},
                                         {'age': 63, 'name': 'Ra Ra Rasputin'},
                                         {'name': 'Jonny B Goode', 'age': 18}],
                                        'age')

        self.assertEqual([sorted(dict.items()) for dict in sorted_dicts],
            [[('age', 63), ('name', 'Ra Ra Rasputin')],
             [('age', 23), ('name', 'Barbara-Ann')],
             [('age', 18), ('name', 'Jonny B Goode')]])

    def test_first(self):
        self.assertEqual(first([0,1,2]), 0)
        self.assertEqual(first(u''), u'')
        self.assertEqual(first(u'test'), u't')

    def test_join(self):
        self.assertEqual(join([0,1,2], u'glue'), u'0glue1glue2')

    def test_length(self):
        self.assertEqual(length(u'1234'), 4)
        self.assertEqual(length([1,2,3,4]), 4)
        self.assertEqual(length_is([], 0), True)
        self.assertEqual(length_is([], 1), False)
        self.assertEqual(length_is('a', 1), True)
        self.assertEqual(length_is(u'a', 10), False)

    def test_slice(self):
        self.assertEqual(slice_(u'abcdefg', u'0'), u'')
        self.assertEqual(slice_(u'abcdefg', u'1'), u'a')
        self.assertEqual(slice_(u'abcdefg', u'-1'), u'abcdef')
        self.assertEqual(slice_(u'abcdefg', u'1:2'), u'b')
        self.assertEqual(slice_(u'abcdefg', u'1:3'), u'bc')
        self.assertEqual(slice_(u'abcdefg', u'0::2'), u'aceg')

    def test_unordered_list(self):
        self.assertEqual(unordered_list([u'item 1', u'item 2']),
            u'\t<li>item 1</li>\n\t<li>item 2</li>')
        self.assertEqual(unordered_list([u'item 1', [u'item 1.1']]),
            u'\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1</li>\n\t</ul>\n\t</li>')

        self.assertEqual(
            unordered_list([u'item 1', [u'item 1.1', u'item1.2'], u'item 2']),
            u'\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1</li>\n\t\t<li>item1.2'\
            u'</li>\n\t</ul>\n\t</li>\n\t<li>item 2</li>')

        self.assertEqual(
            unordered_list([u'item 1', [u'item 1.1', [u'item 1.1.1',
                                                      [u'item 1.1.1.1']]]]),
            u'\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1\n\t\t<ul>\n\t\t\t<li>'\
            u'item 1.1.1\n\t\t\t<ul>\n\t\t\t\t<li>item 1.1.1.1</li>\n\t\t\t'\
            u'</ul>\n\t\t\t</li>\n\t\t</ul>\n\t\t</li>\n\t</ul>\n\t</li>')

        self.assertEqual(unordered_list(
            ['States', ['Kansas', ['Lawrence', 'Topeka'], 'Illinois']]),
            u'\t<li>States\n\t<ul>\n\t\t<li>Kansas\n\t\t<ul>\n\t\t\t<li>'\
            u'Lawrence</li>\n\t\t\t<li>Topeka</li>\n\t\t</ul>\n\t\t</li>'\
            u'\n\t\t<li>Illinois</li>\n\t</ul>\n\t</li>')

        class ULItem(object):
            def __init__(self, title):
              self.title = title
            def __unicode__(self):
                return u'ulitem-%s' % str(self.title)

        a = ULItem('a')
        b = ULItem('b')
        self.assertEqual(unordered_list([a,b]),
                          u'\t<li>ulitem-a</li>\n\t<li>ulitem-b</li>')

        # Old format for unordered lists should still work
        self.assertEqual(unordered_list([u'item 1', []]), u'\t<li>item 1</li>')

        self.assertEqual(unordered_list([u'item 1', [[u'item 1.1', []]]]),
            u'\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1</li>\n\t</ul>\n\t</li>')

        self.assertEqual(unordered_list([u'item 1', [[u'item 1.1', []],
            [u'item 1.2', []]]]), u'\t<li>item 1\n\t<ul>\n\t\t<li>item 1.1'\
            u'</li>\n\t\t<li>item 1.2</li>\n\t</ul>\n\t</li>')

        self.assertEqual(unordered_list(['States', [['Kansas', [['Lawrence',
            []], ['Topeka', []]]], ['Illinois', []]]]), u'\t<li>States\n\t'\
            u'<ul>\n\t\t<li>Kansas\n\t\t<ul>\n\t\t\t<li>Lawrence</li>'\
            u'\n\t\t\t<li>Topeka</li>\n\t\t</ul>\n\t\t</li>\n\t\t<li>'\
            u'Illinois</li>\n\t</ul>\n\t</li>')

    def test_add(self):
        self.assertEqual(add(u'1', u'2'), 3)

    def test_get_digit(self):
        self.assertEqual(get_digit(123, 1), 3)
        self.assertEqual(get_digit(123, 2), 2)
        self.assertEqual(get_digit(123, 3), 1)
        self.assertEqual(get_digit(123, 4), 0)
        self.assertEqual(get_digit(123, 0), 123)
        self.assertEqual(get_digit(u'xyz', 0), u'xyz')

    def test_date(self):
        # real testing of date() is in dateformat.py
        self.assertEqual(date(datetime.datetime(2005, 12, 29), u"d F Y"),
                          u'29 December 2005')
        self.assertEqual(date(datetime.datetime(2005, 12, 29), ur'jS o\f F'),
                          u'29th of December')

    def test_time(self):
        # real testing of time() is done in dateformat.py
        self.assertEqual(time(datetime.time(13), u"h"), u'01')
        self.assertEqual(time(datetime.time(0), u"h"), u'12')

    def test_timesince(self):
        # real testing is done in timesince.py, where we can provide our own 'now'
        self.assertEqual(
            timesince(datetime.datetime.now() - datetime.timedelta(1)),
            u'1 day')

        self.assertEqual(
            timesince(datetime.datetime(2005, 12, 29),
                      datetime.datetime(2005, 12, 30)),
            u'1 day')

    def test_timeuntil(self):
        self.assertEqual(
            timeuntil(datetime.datetime.now() + datetime.timedelta(1)),
            u'1 day')

        self.assertEqual(timeuntil(datetime.datetime(2005, 12, 30),
                                    datetime.datetime(2005, 12, 29)),
                          u'1 day')

    def test_default(self):
        self.assertEqual(default(u"val", u"default"), u'val')
        self.assertEqual(default(None, u"default"), u'default')
        self.assertEqual(default(u'', u"default"), u'default')

    def test_if_none(self):
        self.assertEqual(default_if_none(u"val", u"default"), u'val')
        self.assertEqual(default_if_none(None, u"default"), u'default')
        self.assertEqual(default_if_none(u'', u"default"), u'')

    def test_divisibleby(self):
        self.assertEqual(divisibleby(4, 2), True)
        self.assertEqual(divisibleby(4, 3), False)

    def test_yesno(self):
        self.assertEqual(yesno(True), u'yes')
        self.assertEqual(yesno(False), u'no')
        self.assertEqual(yesno(None), u'maybe')
        self.assertEqual(yesno(True, u'certainly,get out of town,perhaps'),
                          u'certainly')
        self.assertEqual(yesno(False, u'certainly,get out of town,perhaps'),
                          u'get out of town')
        self.assertEqual(yesno(None, u'certainly,get out of town,perhaps'),
                          u'perhaps')
        self.assertEqual(yesno(None, u'certainly,get out of town'),
                          u'get out of town')

    def test_filesizeformat(self):
        self.assertEqual(filesizeformat(1023), u'1023 bytes')
        self.assertEqual(filesizeformat(1024), u'1.0 KB')
        self.assertEqual(filesizeformat(10*1024), u'10.0 KB')
        self.assertEqual(filesizeformat(1024*1024-1), u'1024.0 KB')
        self.assertEqual(filesizeformat(1024*1024), u'1.0 MB')
        self.assertEqual(filesizeformat(1024*1024*50), u'50.0 MB')
        self.assertEqual(filesizeformat(1024*1024*1024-1), u'1024.0 MB')
        self.assertEqual(filesizeformat(1024*1024*1024), u'1.0 GB')
        self.assertEqual(filesizeformat(1024*1024*1024*1024), u'1.0 TB')
        self.assertEqual(filesizeformat(1024*1024*1024*1024*1024), u'1.0 PB')
        self.assertEqual(filesizeformat(1024*1024*1024*1024*1024*2000),
                          u'2000.0 PB')
        self.assertEqual(filesizeformat(complex(1,-1)), u'0 bytes')
        self.assertEqual(filesizeformat(""), u'0 bytes')
        self.assertEqual(filesizeformat(u"\N{GREEK SMALL LETTER ALPHA}"),
                          u'0 bytes')

    def test_localized_filesizeformat(self):
        from django.utils.translation import activate, deactivate
        old_localize = settings.USE_L10N
        try:
            activate('de')
            settings.USE_L10N = True
            self.assertEqual(filesizeformat(1023), u'1023 Bytes')
            self.assertEqual(filesizeformat(1024), u'1,0 KB')
            self.assertEqual(filesizeformat(10*1024), u'10,0 KB')
            self.assertEqual(filesizeformat(1024*1024-1), u'1024,0 KB')
            self.assertEqual(filesizeformat(1024*1024), u'1,0 MB')
            self.assertEqual(filesizeformat(1024*1024*50), u'50,0 MB')
            self.assertEqual(filesizeformat(1024*1024*1024-1), u'1024,0 MB')
            self.assertEqual(filesizeformat(1024*1024*1024), u'1,0 GB')
            self.assertEqual(filesizeformat(1024*1024*1024*1024), u'1,0 TB')
            self.assertEqual(filesizeformat(1024*1024*1024*1024*1024),
                              u'1,0 PB')
            self.assertEqual(filesizeformat(1024*1024*1024*1024*1024*2000),
                              u'2000,0 PB')
            self.assertEqual(filesizeformat(complex(1,-1)), u'0 Bytes')
            self.assertEqual(filesizeformat(""), u'0 Bytes')
            self.assertEqual(filesizeformat(u"\N{GREEK SMALL LETTER ALPHA}"),
                              u'0 Bytes')
        finally:
            deactivate()
            settings.USE_L10N = old_localize

    def test_pluralize(self):
        self.assertEqual(pluralize(1), u'')
        self.assertEqual(pluralize(0), u's')
        self.assertEqual(pluralize(2), u's')
        self.assertEqual(pluralize([1]), u'')
        self.assertEqual(pluralize([]), u's')
        self.assertEqual(pluralize([1,2,3]), u's')
        self.assertEqual(pluralize(1,u'es'), u'')
        self.assertEqual(pluralize(0,u'es'), u'es')
        self.assertEqual(pluralize(2,u'es'), u'es')
        self.assertEqual(pluralize(1,u'y,ies'), u'y')
        self.assertEqual(pluralize(0,u'y,ies'), u'ies')
        self.assertEqual(pluralize(2,u'y,ies'), u'ies')
        self.assertEqual(pluralize(0,u'y,ies,error'), u'')

    def test_phone2numeric(self):
        self.assertEqual(phone2numeric(u'0800 flowers'), u'0800 3569377')

    def test_non_string_input(self):
        # Filters shouldn't break if passed non-strings
        self.assertEqual(addslashes(123), u'123')
        self.assertEqual(linenumbers(123), u'1. 123')
        self.assertEqual(lower(123), u'123')
        self.assertEqual(make_list(123), [u'1', u'2', u'3'])
        self.assertEqual(slugify(123), u'123')
        self.assertEqual(title(123), u'123')
        self.assertEqual(truncatewords(123, 2), u'123')
        self.assertEqual(upper(123), u'123')
        self.assertEqual(urlencode(123), u'123')
        self.assertEqual(urlize(123), u'123')
        self.assertEqual(urlizetrunc(123, 1), u'123')
        self.assertEqual(wordcount(123), 1)
        self.assertEqual(wordwrap(123, 2), u'123')
        self.assertEqual(ljust('123', 4), u'123 ')
        self.assertEqual(rjust('123', 4), u' 123')
        self.assertEqual(center('123', 5), u' 123 ')
        self.assertEqual(center('123', 6), u' 123  ')
        self.assertEqual(cut(123, '2'), u'13')
        self.assertEqual(escape(123), u'123')
        self.assertEqual(linebreaks(123), u'<p>123</p>')
        self.assertEqual(linebreaksbr(123), u'123')
        self.assertEqual(removetags(123, 'a'), u'123')
        self.assertEqual(striptags(123), u'123')

