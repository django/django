"""
>>> floatformat(7.7)
'7.7'
>>> floatformat(7.0)
'7'
>>> floatformat(0.7)
'0.7'
>>> floatformat(0.07)
'0.1'
>>> floatformat(0.007)
'0.0'
>>> floatformat(0.0)
'0'

>>> addslashes('"double quotes" and \\'single quotes\\'')
'\\\\"double quotes\\\\" and \\\\\\'single quotes\\\\\\''

>>> capfirst('hello world')
'Hello world'

>>> fix_ampersands('Jack & Jill & Jeroboam')
'Jack &amp; Jill &amp; Jeroboam'

>>> linenumbers('line 1\\nline 2')
'1. line 1\\n2. line 2'

>>> linenumbers('\\n'.join(['x'] * 10))
'01. x\\n02. x\\n03. x\\n04. x\\n05. x\\n06. x\\n07. x\\n08. x\\n09. x\\n10. x'

>>> lower('TEST')
'test'

>>> lower(u'\\xcb') # uppercase E umlaut
u'\\xeb'

>>> make_list('abc')
['a', 'b', 'c']

>>> make_list(1234)
['1', '2', '3', '4']

>>> slugify(' Jack & Jill like numbers 1,2,3 and 4 and silly characters ?%.$!/')
'jack-jill-like-numbers-123-and-4-and-silly-characters'

>>> stringformat(1, '03d')
'001'

>>> stringformat(1, 'z')
''

>>> title('a nice title, isn\\'t it?')
"A Nice Title, Isn't It?"


>>> truncatewords('A sentence with a few words in it', 1)
'A ...'

>>> truncatewords('A sentence with a few words in it', 5)
'A sentence with a few ...'

>>> truncatewords('A sentence with a few words in it', 100)
'A sentence with a few words in it'

>>> truncatewords('A sentence with a few words in it', 'not a number')
'A sentence with a few words in it'


>>> upper('Mixed case input')
'MIXED CASE INPUT'

>>> upper(u'\\xeb') # lowercase e umlaut
u'\\xcb'


>>> urlencode('jack & jill')
'jack%20%26%20jill'


>>> urlizetrunc('http://short.com/', 20)
'<a href="http://short.com/" rel="nofollow">http://short.com/</a>'

>>> urlizetrunc('http://www.google.co.uk/search?hl=en&q=some+long+url&btnG=Search&meta=', 20)
'<a href="http://www.google.co.uk/search?hl=en&q=some+long+url&btnG=Search&meta=" rel="nofollow">http://www.google.co...</a>'

>>> wordcount('')
0

>>> wordcount('oneword')
1

>>> wordcount('lots of words')
3

>>> wordwrap('this is a long paragraph of text that really needs to be wrapped I\\'m afraid', 14)
"this is a long\\nparagraph of\\ntext that\\nreally needs\\nto be wrapped\\nI'm afraid"

>>> ljust('test', 10)
'test      '

>>> ljust('test', 3)
'test'

>>> rjust('test', 10)
'      test'

>>> rjust('test', 3)
'test'

>>> center('test', 6)
' test '

>>> cut('a string to be mangled', 'a')
' string to be mngled'

>>> cut('a string to be mangled', 'ng')
'a stri to be maled'

>>> cut('a string to be mangled', 'strings')
'a string to be mangled'

>>> escape('<some html & special characters > here')
'&lt;some html &amp; special characters &gt; here'

>>> linebreaks('line 1')
'<p>line 1</p>'

>>> linebreaks('line 1\\nline 2')
'<p>line 1<br />line 2</p>'

>>> removetags('some <b>html</b> with <script>alert("You smell")</script> disallowed <img /> tags', 'script img')
'some <b>html</b> with alert("You smell") disallowed  tags'

>>> striptags('some <b>html</b> with <script>alert("You smell")</script> disallowed <img /> tags')
'some html with alert("You smell") disallowed  tags'

>>> dictsort([{'age': 23, 'name': 'Barbara-Ann'},\
              {'age': 63, 'name': 'Ra Ra Rasputin'},\
              {'name': 'Jonny B Goode', 'age': 18}], 'age')
[{'age': 18, 'name': 'Jonny B Goode'},\
 {'age': 23, 'name': 'Barbara-Ann'},\
 {'age': 63, 'name': 'Ra Ra Rasputin'}]

>>> dictsortreversed([{'age': 23, 'name': 'Barbara-Ann'},\
              {'age': 63, 'name': 'Ra Ra Rasputin'},\
              {'name': 'Jonny B Goode', 'age': 18}], 'age')
[{'age': 63, 'name': 'Ra Ra Rasputin'},\
 {'age': 23, 'name': 'Barbara-Ann'},\
 {'age': 18, 'name': 'Jonny B Goode'}]

>>> first([0,1,2])
0

>>> first('')
''

>>> first('test')
't'

>>> join([0,1,2], 'glue')
'0glue1glue2'

>>> length('1234')
4

>>> length([1,2,3,4])
4

>>> length_is([], 0)
True

>>> length_is([], 1)
False

>>> length_is('a', 1)
True

>>> length_is('a', 10)
False

>>> slice_('abcdefg', '0')
''

>>> slice_('abcdefg', '1')
'a'

>>> slice_('abcdefg', '-1')
'abcdef'

>>> slice_('abcdefg', '1:2')
'b'

>>> slice_('abcdefg', '1:3')
'bc'

>>> slice_('abcdefg', '0::2')
'aceg'

>>> unordered_list(['item 1', []])
'\\t<li>item 1</li>'

>>> unordered_list(['item 1', [['item 1.1', []]]])
'\\t<li>item 1\\n\\t<ul>\\n\\t\\t<li>item 1.1</li>\\n\\t</ul>\\n\\t</li>'

>>> unordered_list(['item 1', [['item 1.1', []], ['item 1.2', []]]])
'\\t<li>item 1\\n\\t<ul>\\n\\t\\t<li>item 1.1</li>\\n\\t\\t<li>item 1.2</li>\\n\\t</ul>\\n\\t</li>'

>>> add('1', '2')
3

>>> get_digit(123, 1)
3

>>> get_digit(123, 2)
2

>>> get_digit(123, 3)
1

>>> get_digit(123, 4)
0

>>> get_digit(123, 0)
123

>>> get_digit('xyz', 0)
'xyz'

# real testing of date() is in dateformat.py
>>> date(datetime.datetime(2005, 12, 29), "d F Y")
'29 December 2005'

# real testing of time() is done in dateformat.py
>>> time(datetime.time(13), "h")
'01'

# real testing is done in timesince.py, where we can provide our own 'now'
>>> timesince(datetime.datetime.now() - datetime.timedelta(1))
'1 day'

>>> default("val", "default")
'val'

>>> default(None, "default")
'default'

>>> default('', "default")
'default'

>>> default_if_none("val", "default")
'val'

>>> default_if_none(None, "default")
'default'

>>> default_if_none('', "default")
''

>>> divisibleby(4, 2)
True

>>> divisibleby(4, 3)
False

>>> yesno(True)
'yes'

>>> yesno(False)
'no'

>>> yesno(None)
'maybe'

>>> yesno(True, 'certainly,get out of town,perhaps')
'certainly'

>>> yesno(False, 'certainly,get out of town,perhaps')
'get out of town'

>>> yesno(None, 'certainly,get out of town,perhaps')
'perhaps'

>>> yesno(None, 'certainly,get out of town')
'get out of town'

>>> filesizeformat(1023)
'1023 bytes'

>>> filesizeformat(1024)
'1.0 KB'

>>> filesizeformat(10*1024)
'10.0 KB'

>>> filesizeformat(1024*1024-1)
'1024.0 KB'

>>> filesizeformat(1024*1024)
'1.0 MB'

>>> filesizeformat(1024*1024*50)
'50.0 MB'

>>> filesizeformat(1024*1024*1024-1)
'1024.0 MB'

>>> filesizeformat(1024*1024*1024)
'1.0 GB'

>>> pluralize(1)
''

>>> pluralize(0)
's'

>>> pluralize(2)
's'

>>> phone2numeric('0800 flowers')
'0800 3569377'



"""

from django.template.defaultfilters import *
import datetime

if __name__ == '__main__':
    import doctest
    doctest.testmod()
