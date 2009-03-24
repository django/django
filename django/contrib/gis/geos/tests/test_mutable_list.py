# Copyright (c) 2008-2009 Aryeh Leib Taurog, all rights reserved.
# Modified from original contribution by Aryeh Leib Taurog, which was
# released under the New BSD license.
import unittest
from django.contrib.gis.geos.mutable_list import ListMixin

class UserListA(ListMixin):
    _mytype = tuple
    def __init__(self, i_list, *args, **kwargs):
        self._list = self._mytype(i_list)
        super(UserListA, self).__init__(*args, **kwargs)

    def __len__(self):  return len(self._list)

    def __iter__(self): return iter(self._list)

    def __str__(self):  return str(self._list)

    def __repr__(self): return repr(self._list)

    def _set_collection(self, length, items):
        # this would work:
        # self._list = self._mytype(items)
        # but then we wouldn't be testing length parameter
        itemList = ['x'] * length
        for i, v in enumerate(items):
            itemList[i] = v

        self._list = self._mytype(itemList)

    def _getitem_external(self, index):
        return self._list[index]

    _getitem_internal = _getitem_external
    _set_single = ListMixin._set_single_rebuild
    _assign_extended_slice = ListMixin._assign_extended_slice_rebuild

class UserListB(UserListA):
    _mytype = list

    def _set_single(self, index, value):
        self._list[index] = value

def nextRange(length):
    nextRange.start += 100
    return range(nextRange.start, nextRange.start + length)

nextRange.start = 0

class ListMixinTest(unittest.TestCase):
    """
    Tests base class ListMixin by comparing a list clone which is
    a ListMixin subclass with a real Python list.
    """
    limit = 3
    listType = UserListA

    @classmethod
    def lists_of_len(cls, length=None):
        if length is None: length = cls.limit
        pl = range(length)
        return pl, cls.listType(pl)

    @classmethod
    def limits_plus(cls, b):
        return range(-cls.limit - b, cls.limit + b)

    @classmethod
    def step_range(cls):
        return range(-1 - cls.limit, 0) + range(1, 1 + cls.limit)

    def test01_getslice(self):
        'Testing slice retrieval'
        pl, ul = self.lists_of_len()
        for i in self.limits_plus(1):
            self.assertEqual(pl[i:], ul[i:], 'slice [%d:]' % (i))
            self.assertEqual(pl[:i], ul[:i], 'slice [:%d]' % (i))

            for j in self.limits_plus(1):
                self.assertEqual(pl[i:j], ul[i:j], 'slice [%d:%d]' % (i,j))
                for k in self.step_range():
                    self.assertEqual(pl[i:j:k], ul[i:j:k], 'slice [%d:%d:%d]' % (i,j,k))

            for k in self.step_range():
                self.assertEqual(pl[i::k], ul[i::k], 'slice [%d::%d]' % (i,k))
                self.assertEqual(pl[:i:k], ul[:i:k], 'slice [:%d:%d]' % (i,k))

        for k in self.step_range():
            self.assertEqual(pl[::k], ul[::k], 'slice [::%d]' % (k))

    def test02_setslice(self):
        'Testing slice assignment'
        def setfcn(x,i,j,k,L): x[i:j:k] = range(L)
        pl, ul = self.lists_of_len()
        for slen in range(self.limit + 1):
            ssl = nextRange(slen)
            ul[:] = ssl
            pl[:] = ssl
            self.assertEqual(pl, ul[:], 'set slice [:]')

            for i in self.limits_plus(1):
                ssl = nextRange(slen)
                ul[i:] = ssl
                pl[i:] = ssl
                self.assertEqual(pl, ul[:], 'set slice [%d:]' % (i))

                ssl = nextRange(slen)
                ul[:i] = ssl
                pl[:i] = ssl
                self.assertEqual(pl, ul[:], 'set slice [:%d]' % (i))

                for j in self.limits_plus(1):
                    ssl = nextRange(slen)
                    ul[i:j] = ssl
                    pl[i:j] = ssl
                    self.assertEqual(pl, ul[:], 'set slice [%d:%d]' % (i, j))

                    for k in self.step_range():
                        ssl = nextRange( len(ul[i:j:k]) )
                        ul[i:j:k] = ssl
                        pl[i:j:k] = ssl
                        self.assertEqual(pl, ul[:], 'set slice [%d:%d:%d]' % (i, j, k))

                        sliceLen = len(ul[i:j:k])
                        self.assertRaises(ValueError, setfcn, ul, i, j, k, sliceLen + 1)
                        if sliceLen > 2:
                            self.assertRaises(ValueError, setfcn, ul, i, j, k, sliceLen - 1)

                for k in self.step_range():
                    ssl = nextRange( len(ul[i::k]) )
                    ul[i::k] = ssl
                    pl[i::k] = ssl
                    self.assertEqual(pl, ul[:], 'set slice [%d::%d]' % (i, k))

                    ssl = nextRange( len(ul[:i:k]) )
                    ul[:i:k] = ssl
                    pl[:i:k] = ssl
                    self.assertEqual(pl, ul[:], 'set slice [:%d:%d]' % (i, k))

            for k in self.step_range():
                ssl = nextRange(len(ul[::k]))
                ul[::k] = ssl
                pl[::k] = ssl
                self.assertEqual(pl, ul[:], 'set slice [::%d]' % (k))


    def test03_delslice(self):
        'Testing delete slice'
        for Len in range(self.limit):
            pl, ul = self.lists_of_len(Len)
            del pl[:]
            del ul[:]
            self.assertEqual(pl[:], ul[:], 'del slice [:]')
            for i in range(-Len - 1, Len + 1):
                pl, ul = self.lists_of_len(Len)
                del pl[i:]
                del ul[i:]
                self.assertEqual(pl[:], ul[:], 'del slice [%d:]' % (i))
                pl, ul = self.lists_of_len(Len)
                del pl[:i]
                del ul[:i]
                self.assertEqual(pl[:], ul[:], 'del slice [:%d]' % (i))
                for j in range(-Len - 1, Len + 1):
                    pl, ul = self.lists_of_len(Len)
                    del pl[i:j]
                    del ul[i:j]
                    self.assertEqual(pl[:], ul[:], 'del slice [%d:%d]' % (i,j))
                    for k in range(-Len - 1,0) + range(1,Len):
                        pl, ul = self.lists_of_len(Len)
                        del pl[i:j:k]
                        del ul[i:j:k]
                        self.assertEqual(pl[:], ul[:], 'del slice [%d:%d:%d]' % (i,j,k))

                for k in range(-Len - 1,0) + range(1,Len):
                    pl, ul = self.lists_of_len(Len)
                    del pl[:i:k]
                    del ul[:i:k]
                    self.assertEqual(pl[:], ul[:], 'del slice [:%d:%d]' % (i,k))

                    pl, ul = self.lists_of_len(Len)
                    del pl[i::k]
                    del ul[i::k]
                    self.assertEqual(pl[:], ul[:], 'del slice [%d::%d]' % (i,k))

            for k in range(-Len - 1,0) + range(1,Len):
                pl, ul = self.lists_of_len(Len)
                del pl[::k]
                del ul[::k]
                self.assertEqual(pl[:], ul[:], 'del slice [::%d]' % (k))

    def test04_get_set_del_single(self):
        'Testing get/set/delete single item'
        pl, ul = self.lists_of_len()
        for i in self.limits_plus(0):
            self.assertEqual(pl[i], ul[i], 'get single item [%d]' % i)

        for i in self.limits_plus(0):
            pl, ul = self.lists_of_len()
            pl[i] = 100
            ul[i] = 100
            self.assertEqual(pl[:], ul[:], 'set single item [%d]' % i)

        for i in self.limits_plus(0):
            pl, ul = self.lists_of_len()
            del pl[i]
            del ul[i]
            self.assertEqual(pl[:], ul[:], 'del single item [%d]' % i)

    def test05_out_of_range_exceptions(self):
        'Testing out of range exceptions'
        def setfcn(x, i): x[i] = 20
        def getfcn(x, i): return x[i]
        def delfcn(x, i): del x[i]
        pl, ul = self.lists_of_len()
        for i in (-1 - self.limit, self.limit):
            self.assertRaises(IndexError, setfcn, ul, i) # 'set index %d' % i)
            self.assertRaises(IndexError, getfcn, ul, i) # 'get index %d' % i)
            self.assertRaises(IndexError, delfcn, ul, i) # 'del index %d' % i)

    def test06_list_methods(self):
        'Testing list methods'
        pl, ul = self.lists_of_len()
        pl.append(40)
        ul.append(40)
        self.assertEqual(pl[:], ul[:], 'append')

        pl.extend(range(50,55))
        ul.extend(range(50,55))
        self.assertEqual(pl[:], ul[:], 'extend')

        for i in self.limits_plus(1):
            pl, ul = self.lists_of_len()
            pl.insert(i,50)
            ul.insert(i,50)
            self.assertEqual(pl[:], ul[:], 'insert at %d' % i)

        for i in self.limits_plus(0):
            pl, ul = self.lists_of_len()
            self.assertEqual(pl.pop(i), ul.pop(i), 'popped value at %d' % i)
            self.assertEqual(pl[:], ul[:], 'after pop at %d' % i)

        pl, ul = self.lists_of_len()
        self.assertEqual(pl.pop(), ul.pop(i), 'popped value')
        self.assertEqual(pl[:], ul[:], 'after pop')

        pl, ul = self.lists_of_len()
        def popfcn(x, i): x.pop(i)
        self.assertRaises(IndexError, popfcn, ul, self.limit)
        self.assertRaises(IndexError, popfcn, ul, -1 - self.limit)

        pl, ul = self.lists_of_len()
        for val in range(self.limit):
            self.assertEqual(pl.index(val), ul.index(val), 'index of %d' % val)

        for val in self.limits_plus(2):
            self.assertEqual(pl.count(val), ul.count(val), 'count %d' % val)

        for val in range(self.limit):
            pl, ul = self.lists_of_len()
            pl.remove(val)
            ul.remove(val)
            self.assertEqual(pl[:], ul[:], 'after remove val %d' % val)

        def indexfcn(x, v): return x.index(v)
        def removefcn(x, v): return x.remove(v)
        self.assertRaises(ValueError, indexfcn, ul, 40)
        self.assertRaises(ValueError, removefcn, ul, 40)

    def test07_allowed_types(self):
        'Testing type-restricted list'
        pl, ul = self.lists_of_len()
        ul._allowed = (int, long)
        ul[1] = 50
        ul[:2] = [60, 70, 80]
        def setfcn(x, i, v): x[i] = v
        self.assertRaises(TypeError, setfcn, ul, 2, 'hello')
        self.assertRaises(TypeError, setfcn, ul, slice(0,3,2), ('hello','goodbye'))

    def test08_min_length(self):
        'Testing length limits'
        pl, ul = self.lists_of_len()
        ul._minlength = 1
        def delfcn(x,i): del x[:i]
        def setfcn(x,i): x[:i] = []
        for i in range(self.limit - ul._minlength + 1, self.limit + 1):
            self.assertRaises(ValueError, delfcn, ul, i)
            self.assertRaises(ValueError, setfcn, ul, i)
        del ul[:ul._minlength]

        ul._maxlength = 4
        for i in range(0, ul._maxlength - len(ul)):
            ul.append(i)
        self.assertRaises(ValueError, ul.append, 10)

    def test09_iterable_check(self):
        'Testing error on assigning non-iterable to slice'
        pl, ul = self.lists_of_len(self.limit + 1)
        def setfcn(x, i, v): x[i] = v
        self.assertRaises(TypeError, setfcn, ul, slice(0,3,2), 2)

    def test10_checkindex(self):
        'Testing index check'
        pl, ul = self.lists_of_len()
        for i in self.limits_plus(0):
            if i < 0:
                self.assertEqual(ul._checkindex(i), i + self.limit, '_checkindex(neg index)')
            else:
                self.assertEqual(ul._checkindex(i), i, '_checkindex(pos index)')

        for i in (-self.limit - 1, self.limit):
            self.assertRaises(IndexError, ul._checkindex, i)

        ul._IndexError = TypeError
        self.assertRaises(TypeError, ul._checkindex, -self.limit - 1)

class ListMixinTestSingle(ListMixinTest):
    listType = UserListB

def suite():
    s = unittest.TestSuite()
    s.addTest(unittest.makeSuite(ListMixinTest))
    s.addTest(unittest.makeSuite(ListMixinTestSingle))
    return s

def run(verbosity=2):
    unittest.TextTestRunner(verbosity=verbosity).run(suite())

if __name__ == '__main__':
    run()
