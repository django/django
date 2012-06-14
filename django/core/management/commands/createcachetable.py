from optparse import make_option

from django.core.cache.backends.db import BaseDatabaseCache
from django.core.management.base import LabelCommand, CommandError
from django.core.management.color import no_style
from django.db import connections, router, transaction, DEFAULT_DB_ALIAS
from django.db.utils import DatabaseError
from django.utils.encoding import force_unicode


class Command(LabelCommand):
    help = "Creates the table needed to use the SQL cache backend."
    args = "<tablename>"
    label = 'tablename'

    option_list = LabelCommand.option_list + (
        make_option('--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS, help='Nominates a database onto '
                'which the cache table will be installed. '
                'Defaults to the "default" database.'),
    )

    requires_model_validation = False

    def handle_label(self, tablename, **options):
        db = options.get('database')
        cache = BaseDatabaseCache(tablename, {})
        if not router.allow_syncdb(db, cache.cache_model_class):
            return
        connection = connections[db]
        creation = connection.creation
        style = no_style()
        tbl_output, _ = creation.sql_create_model(cache.cache_model_class,
                                           style)
        index_output = creation.sql_indexes_for_model(cache.cache_model_class,
                                                      style)
        curs = connection.cursor()
        try:
            for statement in tbl_output:
                curs.execute(statement)
        except DatabaseError as e:
            transaction.rollback_unless_managed(using=db)
            raise CommandError(
                "Cache table '%s' could not be created.\nThe error was: %s." %
                    (tablename, force_unicode(e)))
        for statement in index_output:
            curs.execute(statement)
        transaction.commit_unless_managed(using=db)
