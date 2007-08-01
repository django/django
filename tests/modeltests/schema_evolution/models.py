"""
Schema Evolution Tests
"""

from django.db import models
from django.conf import settings

GENDER_CHOICES = (
    ('M', 'Male'),
    ('F', 'Female'),
)

class Person(models.Model):
    name = models.CharField(maxlength=20)
    gender = models.CharField(maxlength=1, choices=GENDER_CHOICES)
    gender2 = models.CharField(maxlength=1, choices=GENDER_CHOICES, aka='gender_old')

    def __unicode__(self):
        return self.name
    
    class Meta:
        aka = ('PersonOld', 'OtherBadName')

__test__ = {'API_TESTS':"""
>>> import django
>>> from django.core import management
>>> from django.db import backend, models
>>> from django.db import connection, get_introspection_module
>>> app = models.get_apps()[-1]
>>> cursor = connection.cursor()
"""}

if settings.DATABASE_ENGINE == 'mysql':
    __test__['API_TESTS'] += """
# the table as it is supposed to be
>>> create_table_sql = management.get_sql_all(app)
>>> print create_table_sql
['CREATE TABLE `schema_evolution_person` (\\n    `id` integer AUTO_INCREMENT NOT NULL PRIMARY KEY,\\n    `name` varchar(20) NOT NULL,\\n    `gender` varchar(1) NOT NULL,\\n    `gender2` varchar(1) NOT NULL\\n)\\n;']

# make sure we don't evolve an unedited table
>>> management.get_sql_evolution(app)
[]

# delete a column, so it looks like we've recently added a field
>>> sql = backend.get_drop_column_sql( 'schema_evolution_person', 'gender' )
>>> print sql
ALTER TABLE `schema_evolution_person` DROP COLUMN `gender`;
>>> cursor.execute(sql)
0L
>>> management.get_sql_evolution(app)
['ALTER TABLE `schema_evolution_person` ADD COLUMN `gender` varchar(1) NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])
0L\n0L

# add a column, so it looks like we've recently deleted a field
>>> cursor.execute('ALTER TABLE `schema_evolution_person` ADD COLUMN `gender_nothere` varchar(1) NOT NULL;')
0L
>>> management.get_sql_evolution(app)
['-- warning: as the following may cause data loss, it/they must be run manually', u'-- ALTER TABLE `schema_evolution_person` DROP COLUMN `gender_nothere`;', '-- end warning']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])
0L\n0L

# rename column, so it looks like we've recently renamed a field
>>> cursor.execute('ALTER TABLE `schema_evolution_person` CHANGE COLUMN `gender2` `gender_old` varchar(1) NOT NULL;')
0L
>>> management.get_sql_evolution(app)
['ALTER TABLE `schema_evolution_person` CHANGE COLUMN `gender_old` `gender2` varchar(1) NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])
0L\n0L

# rename table, so it looks like we've recently renamed a model
>>> cursor.execute('ALTER TABLE `schema_evolution_person` RENAME TO `schema_evolution_personold`')
0L
>>> management.get_sql_evolution(app)
['ALTER TABLE `schema_evolution_personold` RENAME TO `schema_evolution_person`;']

# reset the db
>>> cursor.execute(create_table_sql[0])
0L

# change column flags, so it looks like we've recently changed a column flag
>>> cursor.execute('ALTER TABLE `schema_evolution_person` MODIFY COLUMN `name` varchar(10) NULL;')
0L
>>> management.get_sql_evolution(app)
['ALTER TABLE `schema_evolution_person` MODIFY COLUMN `name` varchar(20) NOT NULL;']
"""

if settings.DATABASE_ENGINE == 'postgresql':
    __test__['API_TESTS'] += """
# the table as it is supposed to be
>>> create_table_sql = management.get_sql_all(app)
>>> print create_table_sql
['CREATE TABLE "schema_evolution_person" (\\n    "id" serial NOT NULL PRIMARY KEY,\\n    "name" varchar(20) NOT NULL,\\n    "gender" varchar(1) NOT NULL,\\n    "gender2" varchar(1) NOT NULL\\n)\\n;']

# make sure we don't evolve an unedited table
>>> management.get_sql_evolution(app)
[]

# delete a column, so it looks like we've recently added a field
>>> cursor.execute( backend.get_drop_column_sql( 'schema_evolution_person', 'gender' ) )
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_person" ADD COLUMN "gender" varchar(1);\\nALTER TABLE "schema_evolution_person" ALTER COLUMN "gender" SET NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])

# add a column, so it looks like we've recently deleted a field
>>> cursor.execute( backend.get_add_column_sql( 'schema_evolution_person', 'gender_nothere', 'varchar(1)', True, False, False ) )
>>> management.get_sql_evolution(app)
['-- warning: as the following may cause data loss, it/they must be run manually', u'-- ALTER TABLE "schema_evolution_person" DROP COLUMN "gender_nothere";', '-- end warning']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])

# rename column, so it looks like we've recently renamed a field
>>> cursor.execute( backend.get_change_column_name_sql( 'schema_evolution_person', {}, 'gender2', 'gender_old', 'varchar(1)' ) )
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_person" RENAME COLUMN "gender_old" TO "gender2";']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])

# rename table, so it looks like we've recently renamed a model
>>> cursor.execute( backend.get_change_table_name_sql( 'schema_evolution_personold', 'schema_evolution_person' ) )
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_personold" RENAME TO "schema_evolution_person";']

# reset the db
>>> cursor.execute(create_table_sql[0])

# change column flags, so it looks like we've recently changed a column flag
>>> cursor.execute( backend.get_change_column_def_sql( 'schema_evolution_person', 'name', 'varchar(10)', True, False, False ) )
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_person" ADD COLUMN "name_tmp" varchar(20);\\nUPDATE "schema_evolution_person" SET "name_tmp" = "name";\\nALTER TABLE "schema_evolution_person" DROP COLUMN "name";\\nALTER TABLE "schema_evolution_person" RENAME COLUMN "name_tmp" TO "name";\\nALTER TABLE "schema_evolution_person" ALTER COLUMN "name" SET NOT NULL;']

"""

