class Migration(object):
    """
    The base class for all migrations.

    Migration files will import this from django.db.migrations.Migration
    and subclass it as a class called Migration. It will have one or more
    of the following attributes:

     - operations: A list of Operation instances, probably from django.db.migrations.operations
     - dependencies: A list of tuples of (app_path, migration_name)
     - run_before: A list of tuples of (app_path, migration_name)
     - replaces: A list of migration_names
    """

    # Operations to apply during this migration, in order.
    operations = []

    # Other migrations that should be run before this migration.
    # Should be a list of (app, migration_name).
    dependencies = []

    # Other migrations that should be run after this one (i.e. have
    # this migration added to their dependencies). Useful to make third-party
    # apps' migrations run after your AUTH_USER replacement, for example.
    run_before = []

    # Migration names in this app that this migration replaces. If this is
    # non-empty, this migration will only be applied if all these migrations
    # are not applied.
    replaces = []
