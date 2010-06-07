import copy
import pickle
import unittest
from django.http import QueryDict, HttpResponse, CompatCookie, BadHeaderError

class QueryDictTests(unittest.TestCase):
    def test_missing_key(self):
        q = QueryDict('')
        self.assertRaises(KeyError, q.__getitem__, 'foo')

    def test_immutability(self):
        q = QueryDict('')
        self.assertRaises(AttributeError, q.__setitem__, 'something', 'bar')
        self.assertRaises(AttributeError, q.setlist, 'foo', ['bar'])
        self.assertRaises(AttributeError, q.appendlist, 'foo', ['bar'])
        self.assertRaises(AttributeError, q.update, {'foo': 'bar'})
        self.assertRaises(AttributeError, q.pop, 'foo')
        self.assertRaises(AttributeError, q.popitem)
        self.assertRaises(AttributeError, q.clear)
        
    def test_immutable_get_with_default(self):
        q = QueryDict('')
        self.assertEqual(q.get('foo', 'default'), 'default')

    def test_immutable_basic_operations(self):
        q = QueryDict('')
        self.assertEqual(q.getlist('foo'), [])
        self.assertEqual(q.has_key('foo'), False)
        self.assertEqual('foo' in q, False)
        self.assertEqual(q.items(), [])
        self.assertEqual(q.lists(), [])
        self.assertEqual(q.items(), [])
        self.assertEqual(q.keys(), [])
        self.assertEqual(q.values(), [])
        self.assertEqual(len(q), 0)
        self.assertEqual(q.urlencode(), '')
        
    def test_single_key_value(self):
        """Test QueryDict with one key/value pair"""

        q = QueryDict('foo=bar')
        self.assertEqual(q['foo'], 'bar')
        self.assertRaises(KeyError, q.__getitem__, 'bar')
        self.assertRaises(AttributeError, q.__setitem__, 'something', 'bar')

        self.assertEqual(q.get('foo', 'default'), 'bar')
        self.assertEqual(q.get('bar', 'default'), 'default')
        self.assertEqual(q.getlist('foo'), ['bar'])
        self.assertEqual(q.getlist('bar'), [])
        
        self.assertRaises(AttributeError, q.setlist, 'foo', ['bar'])
        self.assertRaises(AttributeError, q.appendlist, 'foo', ['bar'])

        self.failUnless(q.has_key('foo'))
        self.failUnless('foo' in q)
        self.failIf(q.has_key('bar'))
        self.failIf('bar' in q)

        self.assertEqual(q.items(), [(u'foo', u'bar')])
        self.assertEqual(q.lists(), [(u'foo', [u'bar'])])
        self.assertEqual(q.keys(), ['foo'])
        self.assertEqual(q.values(), ['bar'])
        self.assertEqual(len(q), 1)

        self.assertRaises(AttributeError, q.update, {'foo': 'bar'})
        self.assertRaises(AttributeError, q.pop, 'foo')
        self.assertRaises(AttributeError, q.popitem)
        self.assertRaises(AttributeError, q.clear)
        self.assertRaises(AttributeError, q.setdefault, 'foo', 'bar')
        
        self.assertEqual(q.urlencode(), 'foo=bar')
        
    def test_mutable_copy(self):
        """A copy of a QueryDict is mutable."""
        q = QueryDict('').copy()
        self.assertRaises(KeyError, q.__getitem__, "foo")
        q['name'] = 'john'
        self.assertEqual(q['name'], 'john')
        
    def test_mutable_delete(self):
        q = QueryDict('').copy()
        q['name'] = 'john'
        del q['name']
        self.failIf('name' in q)

    def test_basic_mutable_operations(self):
        q = QueryDict('').copy()
        q['name'] = 'john'
        self.assertEqual(q.get('foo', 'default'), 'default')
        self.assertEqual(q.get('name', 'default'), 'john')
        self.assertEqual(q.getlist('name'), ['john'])
        self.assertEqual(q.getlist('foo'), [])

        q.setlist('foo', ['bar', 'baz'])
        self.assertEqual(q.get('foo', 'default'), 'baz')
        self.assertEqual(q.getlist('foo'), ['bar', 'baz'])

        q.appendlist('foo', 'another')
        self.assertEqual(q.getlist('foo'), ['bar', 'baz', 'another'])
        self.assertEqual(q['foo'], 'another')
        self.failUnless(q.has_key('foo'))
        self.failUnless('foo' in q)

        self.assertEqual(q.items(),  [(u'foo', u'another'), (u'name', u'john')])
        self.assertEqual(q.lists(), [(u'foo', [u'bar', u'baz', u'another']), (u'name', [u'john'])])
        self.assertEqual(q.keys(), [u'foo', u'name'])
        self.assertEqual(q.values(), [u'another', u'john'])
        self.assertEqual(len(q), 2)

        q.update({'foo': 'hello'})
        self.assertEqual(q['foo'], 'hello')
        self.assertEqual(q.get('foo', 'not available'), 'hello')
        self.assertEqual(q.getlist('foo'), [u'bar', u'baz', u'another', u'hello'])
        self.assertEqual(q.pop('foo'), [u'bar', u'baz', u'another', u'hello'])
        self.assertEqual(q.pop('foo', 'not there'), 'not there')
        self.assertEqual(q.get('foo', 'not there'), 'not there')
        self.assertEqual(q.setdefault('foo', 'bar'), 'bar')
        self.assertEqual(q['foo'], 'bar')
        self.assertEqual(q.getlist('foo'), ['bar'])
        self.assertEqual(q.urlencode(), 'foo=bar&name=john')

        q.clear()
        self.assertEqual(len(q), 0)

    def test_multiple_keys(self):
        """Test QueryDict with two key/value pairs with same keys."""

        q = QueryDict('vote=yes&vote=no')
        
        self.assertEqual(q['vote'], u'no')
        self.assertRaises(AttributeError, q.__setitem__, 'something', 'bar')
                
        self.assertEqual(q.get('vote', 'default'), u'no')
        self.assertEqual(q.get('foo', 'default'), 'default')
        self.assertEqual(q.getlist('vote'), [u'yes', u'no'])
        self.assertEqual(q.getlist('foo'), [])
        
        self.assertRaises(AttributeError, q.setlist, 'foo', ['bar', 'baz'])
        self.assertRaises(AttributeError, q.setlist, 'foo', ['bar', 'baz'])
        self.assertRaises(AttributeError, q.appendlist, 'foo', ['bar'])

        self.assertEqual(q.has_key('vote'), True)        
        self.assertEqual('vote' in q, True)
        self.assertEqual(q.has_key('foo'), False)
        self.assertEqual('foo' in q, False)
        self.assertEqual(q.items(), [(u'vote', u'no')])
        self.assertEqual(q.lists(), [(u'vote', [u'yes', u'no'])])
        self.assertEqual(q.keys(), [u'vote'])
        self.assertEqual(q.values(), [u'no'])
        self.assertEqual(len(q), 1)
        
        self.assertRaises(AttributeError, q.update, {'foo': 'bar'})
        self.assertRaises(AttributeError, q.pop, 'foo')
        self.assertRaises(AttributeError, q.popitem)
        self.assertRaises(AttributeError, q.clear)
        self.assertRaises(AttributeError, q.setdefault, 'foo', 'bar')
        self.assertRaises(AttributeError, q.__delitem__, 'vote')
        
    def test_invalid_input_encoding(self):
        """
        QueryDicts must be able to handle invalid input encoding (in this
        case, bad UTF-8 encoding).
        """
        q = QueryDict('foo=bar&foo=\xff')
        self.assertEqual(q['foo'], u'\ufffd')        
        self.assertEqual(q.getlist('foo'), [u'bar', u'\ufffd'])
   
    def test_pickle(self):
        q = QueryDict('')
        q1 = pickle.loads(pickle.dumps(q, 2))
        self.assertEqual(q == q1, True)
        q = QueryDict('a=b&c=d')
        q1 = pickle.loads(pickle.dumps(q, 2))
        self.assertEqual(q == q1, True)
        q = QueryDict('a=b&c=d&a=1') 
        q1 = pickle.loads(pickle.dumps(q, 2))
        self.assertEqual(q == q1 , True)

    def test_update_from_querydict(self):
        """Regression test for #8278: QueryDict.update(QueryDict)"""
        x = QueryDict("a=1&a=2", mutable=True)
        y = QueryDict("a=3&a=4")
        x.update(y)
        self.assertEqual(x.getlist('a'), [u'1', u'2', u'3', u'4'])    

    def test_non_default_encoding(self):
        """#13572 - QueryDict with a non-default encoding"""
        q = QueryDict('sbb=one', encoding='rot_13') 
        self.assertEqual(q.encoding , 'rot_13' )
        self.assertEqual(q.items() , [(u'foo', u'bar')] )
        self.assertEqual(q.urlencode() , 'sbb=one' )
        q = q.copy() 
        self.assertEqual(q.encoding , 'rot_13' )
        self.assertEqual(q.items() , [(u'foo', u'bar')] )
        self.assertEqual(q.urlencode() , 'sbb=one' )
        self.assertEqual(copy.copy(q).encoding , 'rot_13' )
        self.assertEqual(copy.deepcopy(q).encoding , 'rot_13')
        
class HttpResponseTests(unittest.TestCase):
    def test_unicode_headers(self):
        r = HttpResponse()

        # If we insert a unicode value it will be converted to an ascii
        r['value'] = u'test value'
        self.failUnless(isinstance(r['value'], str))
        
        # An error is raised When a unicode object with non-ascii is assigned.
        self.assertRaises(UnicodeEncodeError, r.__setitem__, 'value', u't\xebst value')
        
        # The response also converts unicode keys to strings.)      
        r[u'test'] = 'testing key'
        l = list(r.items())
        l.sort()
        self.assertEqual(l[1], ('test', 'testing key'))
        
        # It will also raise errors for keys with non-ascii data.
        self.assertRaises(UnicodeEncodeError, r.__setitem__, u't\xebst key', 'value')

    def test_newlines_in_headers(self):
        # Bug #10188: Do not allow newlines in headers (CR or LF)
        r = HttpResponse()
        self.assertRaises(BadHeaderError, r.__setitem__, 'test\rstr', 'test')
        self.assertRaises(BadHeaderError, r.__setitem__, 'test\nstr', 'test')

class CookieTests(unittest.TestCase):
    def test_encode(self):
        """
        Test that we don't output tricky characters in encoded value
        """
        # Python 2.4 compatibility note: Python 2.4's cookie implementation
        # always returns Set-Cookie headers terminating in semi-colons.
        # That's not the bug this test is looking for, so ignore it.
        c = CompatCookie()
        c['test'] = "An,awkward;value"
        self.assert_(";" not in c.output().rstrip(';')) # IE compat
        self.assert_("," not in c.output().rstrip(';')) # Safari compat

    def test_decode(self):
        """
        Test that we can still preserve semi-colons and commas
        """
        c = CompatCookie()
        c['test'] = "An,awkward;value"
        c2 = CompatCookie()
        c2.load(c.output())
        self.assertEqual(c['test'].value, c2['test'].value)

    def test_decode_2(self):
        """
        Test that we haven't broken normal encoding
        """
        c = CompatCookie()
        c['test'] = "\xf0"
        c2 = CompatCookie()
        c2.load(c.output())
        self.assertEqual(c['test'].value, c2['test'].value)
