"""
Testing some internals of the template processing. These are *not* examples to be copied in user code.
"""

token_parsing=r"""
Tests for TokenParser behavior in the face of quoted strings with spaces.

>>> from django.template import TokenParser


Test case 1: {% tag thevar|filter sometag %}

>>> p = TokenParser("tag thevar|filter sometag")
>>> p.tagname
'tag'
>>> p.value()
'thevar|filter'
>>> p.more()
True
>>> p.tag()
'sometag'
>>> p.more()
False

Test case 2: {% tag "a value"|filter sometag %}

>>> p = TokenParser('tag "a value"|filter sometag')
>>> p.tagname
'tag'
>>> p.value()
'"a value"|filter'
>>> p.more()
True
>>> p.tag()
'sometag'
>>> p.more()
False

Test case 3: {% tag 'a value'|filter sometag %}

>>> p = TokenParser("tag 'a value'|filter sometag")
>>> p.tagname
'tag'
>>> p.value()
"'a value'|filter"
>>> p.more()
True
>>> p.tag()
'sometag'
>>> p.more()
False
"""

filter_parsing = r"""
>>> from django.template import FilterExpression, Parser

>>> c = {'article': {'section': u'News'}}
>>> p = Parser("")
>>> def fe_test(s): return FilterExpression(s, p).resolve(c)

>>> fe_test('article.section')
u'News'
>>> fe_test('article.section|upper')
u'NEWS'
>>> fe_test(u'"News"')
u'News'
>>> fe_test(u"'News'")
u'News'
>>> fe_test(ur'"Some \"Good\" News"')
u'Some "Good" News'
>>> fe_test(ur"'Some \'Bad\' News'")
u"Some 'Bad' News"

>>> fe = FilterExpression(ur'"Some \"Good\" News"', p)
>>> fe.filters
[]
>>> fe.var
u'Some "Good" News'
"""

variable_parsing = r"""
>>> from django.template import Variable

>>> c = {'article': {'section': u'News'}}
>>> Variable('article.section').resolve(c)
u'News'
>>> Variable(u'"News"').resolve(c)
u'News'
>>> Variable(u"'News'").resolve(c)
u'News'

Translated strings are handled correctly.

>>> Variable('_(article.section)').resolve(c)
u'News'
>>> Variable('_("Good News")').resolve(c)
u'Good News'
>>> Variable("_('Better News')").resolve(c)
u'Better News'

Escaped quotes work correctly as well.

>>> Variable(ur'"Some \"Good\" News"').resolve(c)
u'Some "Good" News'
>>> Variable(ur"'Some \'Better\' News'").resolve(c)
u"Some 'Better' News"

"""
