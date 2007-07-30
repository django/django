"""
Schema Evolution Tests
"""

from django.db import models

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


"""}

