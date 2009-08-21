from django.conf import settings
from django.db import connection
from django.test import TestCase
from django.utils import functional

from models import Reporter, Article

try:
    set
except NameError:
    from sets import Set as set     # Python 2.3 fallback

#
# The introspection module is optional, so methods tested here might raise
# NotImplementedError. This is perfectly acceptable behavior for the backend
# in question, but the tests need to handle this without failing. Ideally we'd
# skip these tests, but until #4788 is done we'll just ignore them.
#
# The easiest way to accomplish this is to decorate every test case with a
# wrapper that ignores the exception.
#
# The metaclass is just for fun.
#

def ignore_not_implemented(func):
    def _inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NotImplementedError:
            return None
    functional.update_wrapper(_inner, func)
    return _inner

class IgnoreNotimplementedError(type):
    def __new__(cls, name, bases, attrs):
        for k,v in attrs.items():
            if k.startswith('test'):
                attrs[k] = ignore_not_implemented(v)
        return type.__new__(cls, name, bases, attrs)

class IntrospectionTests(TestCase):
    __metaclass__ = IgnoreNotimplementedError

    def test_table_names(self):
        tl = connection.introspection.table_names()
        self.assert_(Reporter._meta.db_table in tl,
                     "'%s' isn't in table_list()." % Reporter._meta.db_table)
        self.assert_(Article._meta.db_table in tl,
                     "'%s' isn't in table_list()." % Article._meta.db_table)

    def test_django_table_names(self):
        cursor = connection.cursor()
        cursor.execute('CREATE TABLE django_ixn_test_table (id INTEGER);');
        tl = connection.introspection.django_table_names()
        cursor.execute("DROP TABLE django_ixn_test_table;")
        self.assert_('django_ixn_testcase_table' not in tl,
                     "django_table_names() returned a non-Django table")

    def test_installed_models(self):
        tables = [Article._meta.db_table, Reporter._meta.db_table]
        models = connection.introspection.installed_models(tables)
        self.assertEqual(models, set([Article, Reporter]))

    def test_sequence_list(self):
        sequences = connection.introspection.sequence_list()
        expected = {'table': Reporter._meta.db_table, 'column': 'id'}
        self.assert_(expected in sequences,
                     'Reporter sequence not found in sequence_list()')

    def test_get_table_description_names(self):
        cursor = connection.cursor()
        desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        self.assertEqual([r[0] for r in desc],
                         [f.column for f in Reporter._meta.fields])

    def test_get_table_description_types(self):
        cursor = connection.cursor()
        desc = connection.introspection.get_table_description(cursor, Reporter._meta.db_table)
        self.assertEqual([datatype(r[1], r) for r in desc],
                          ['IntegerField', 'CharField', 'CharField', 'CharField'])

    # Regression test for #9991 - 'real' types in postgres
    if settings.DATABASE_ENGINE.startswith('postgresql'):
        def test_postgresql_real_type(self):
            cursor = connection.cursor()
            cursor.execute("CREATE TABLE django_ixn_real_test_table (number REAL);")
            desc = connection.introspection.get_table_description(cursor, 'django_ixn_real_test_table')
            cursor.execute('DROP TABLE django_ixn_real_test_table;')
            self.assertEqual(datatype(desc[0][1], desc[0]), 'FloatField')

    def test_get_relations(self):
        cursor = connection.cursor()
        relations = connection.introspection.get_relations(cursor, Article._meta.db_table)

        # Older versions of MySQL don't have the chops to report on this stuff,
        # so just skip it if no relations come back. If they do, though, we
        # should test that the response is correct.
        if relations:
            # That's {field_index: (field_index_other_table, other_table)}
            self.assertEqual(relations, {3: (0, Reporter._meta.db_table)})

    def test_get_indexes(self):
        cursor = connection.cursor()
        indexes = connection.introspection.get_indexes(cursor, Article._meta.db_table)
        self.assertEqual(indexes['reporter_id'], {'unique': False, 'primary_key': False})


def datatype(dbtype, description):
    """Helper to convert a data type into a string."""
    dt = connection.introspection.get_field_type(dbtype, description)
    if type(dt) is tuple:
        return dt[0]
    else:
        return dt
