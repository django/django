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

class Muebles(models.Model):
    tipo = models.CharField(maxlength=40, default="woot")
    # new fields
    fecha_publicacion = models.DateTimeField('date published')

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

# make sure we don't evolve an unedited table
>>> management.get_sql_evolution(app)
[]

# delete a column, so it looks like we've recently added a field
>>> sql = backend.get_drop_column_sql( 'schema_evolution_person', 'gender' )
>>> print sql
['ALTER TABLE `schema_evolution_person` DROP COLUMN `gender`;']
>>> for s in sql: cursor.execute(s)
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
['-- warning: the following may cause data loss', u'ALTER TABLE `schema_evolution_person` DROP COLUMN `gender_nothere`;', '-- end warning']

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

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])
0L\n0L

# delete a datetime column, so it looks like we've recently added a datetime field
>>> for sql in backend.get_drop_column_sql( 'schema_evolution_muebles', 'fecha_publicacion' ): print sql; cursor.execute(sql)
ALTER TABLE `schema_evolution_muebles` DROP COLUMN `fecha_publicacion`;
0L
>>> management.get_sql_evolution(app)
['ALTER TABLE `schema_evolution_muebles` ADD COLUMN `fecha_publicacion` datetime NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_muebles;'); cursor.execute(create_table_sql[1])
0L\n0L

# delete a column with a default value, so it looks like we've recently added a column
>>> for sql in backend.get_drop_column_sql( 'schema_evolution_muebles', 'tipo' ): print sql; cursor.execute(sql)
ALTER TABLE `schema_evolution_muebles` DROP COLUMN `tipo`;
0L
>>> management.get_sql_evolution(app)
['ALTER TABLE `schema_evolution_muebles` ADD COLUMN `tipo` varchar(40) NOT NULL DEFAULT `woot`;']

"""

if settings.DATABASE_ENGINE == 'postgresql' or settings.DATABASE_ENGINE == 'postgresql_psycopg2' :
    __test__['API_TESTS'] += """
# the table as it is supposed to be
>>> create_table_sql = management.get_sql_all(app)

# make sure we don't evolve an unedited table
>>> management.get_sql_evolution(app)
[]

# delete a column, so it looks like we've recently added a field
>>> for sql in backend.get_drop_column_sql( 'schema_evolution_person', 'gender' ): cursor.execute(sql)
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_person" ADD COLUMN "gender" varchar(1);', 'ALTER TABLE "schema_evolution_person" ALTER COLUMN "gender" SET NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])

# add a column, so it looks like we've recently deleted a field
>>> for sql in backend.get_add_column_sql( 'schema_evolution_person', 'gender_nothere', 'varchar(1)', True, False, False, None ): cursor.execute(sql)
>>> management.get_sql_evolution(app)
['-- warning: the following may cause data loss', u'ALTER TABLE "schema_evolution_person" DROP COLUMN "gender_nothere";', '-- end warning']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])

# rename column, so it looks like we've recently renamed a field
>>> for sql in backend.get_change_column_name_sql( 'schema_evolution_person', {}, 'gender2', 'gender_old', 'varchar(1)' ): cursor.execute(sql)
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_person" RENAME COLUMN "gender_old" TO "gender2";']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])

# rename table, so it looks like we've recently renamed a model
>>> for sql in backend.get_change_table_name_sql( 'schema_evolution_personold', 'schema_evolution_person' ): cursor.execute(sql)
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_personold" RENAME TO "schema_evolution_person";']

# reset the db
>>> cursor.execute(create_table_sql[0])

# change column flags, so it looks like we've recently changed a column flag
>>> for sql in backend.get_change_column_def_sql( 'schema_evolution_person', 'name', 'varchar(10)', True, False, False, None ): cursor.execute(sql)
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_person" ADD COLUMN "name_tmp" varchar(20);', 'UPDATE "schema_evolution_person" SET "name_tmp" = "name";', 'ALTER TABLE "schema_evolution_person" DROP COLUMN "name";', 'ALTER TABLE "schema_evolution_person" RENAME COLUMN "name_tmp" TO "name";', 'ALTER TABLE "schema_evolution_person" ALTER COLUMN "name" SET NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;'); cursor.execute(create_table_sql[0])

# delete a datetime column pair, so it looks like we've recently added a datetime field
>>> for sql in backend.get_drop_column_sql( 'schema_evolution_muebles', 'fecha_publicacion' ): print sql; cursor.execute(sql)
ALTER TABLE "schema_evolution_muebles" DROP COLUMN "fecha_publicacion";
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_muebles" ADD COLUMN "fecha_publicacion" timestamp with time zone;', 'ALTER TABLE "schema_evolution_muebles" ALTER COLUMN "fecha_publicacion" SET NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_muebles;'); cursor.execute(create_table_sql[1])

# delete a column with a default value, so it looks like we've recently added a column
>>> for sql in backend.get_drop_column_sql( 'schema_evolution_muebles', 'tipo' ): print sql; cursor.execute(sql)
ALTER TABLE "schema_evolution_muebles" DROP COLUMN "tipo";
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_muebles" ADD COLUMN "tipo" varchar(40);', 'ALTER TABLE "schema_evolution_muebles" ALTER COLUMN "tipo" SET DEFAULT "woot";', 'ALTER TABLE "schema_evolution_muebles" ALTER COLUMN "tipo" SET NOT NULL;']
"""

if settings.DATABASE_ENGINE == 'sqlite3':
    __test__['API_TESTS'] += """
# the table as it is supposed to be
>>> create_table_sql = management.get_sql_all(app)

# make sure we don't evolve an unedited table
>>> management.get_sql_evolution(app)
[]

# delete a column, so it looks like we've recently added a field
>>> cursor.execute( 'DROP TABLE "schema_evolution_person";' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute( 'CREATE TABLE "schema_evolution_person" ( "id" integer NOT NULL UNIQUE PRIMARY KEY, "name" varchar(20) NOT NULL, "gender" varchar(1) NOT NULL );' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_person" ADD COLUMN "gender2" varchar(1) NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# add a column, so it looks like we've recently deleted a field
>>> cursor.execute( 'DROP TABLE "schema_evolution_person";' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute( 'CREATE TABLE "schema_evolution_person" ( "id" integer NOT NULL UNIQUE PRIMARY KEY, "name" varchar(20) NOT NULL, "gender" varchar(1) NOT NULL, "gender2" varchar(1) NOT NULL, "gender_new" varchar(1) NOT NULL );' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute( 'insert into "schema_evolution_person" values (1,2,3,4,5);' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> sql = management.get_sql_evolution(app)
>>> print sql
['-- warning: the following may cause data loss', u'-- FYI: sqlite does not support deleting columns, so we create a new "gender_new" and delete the old  (ie, this could take a while)', 'ALTER TABLE "schema_evolution_person" RENAME TO "schema_evolution_person_1337_TMP";', 'CREATE TABLE "schema_evolution_person" (\\n    "id" integer NOT NULL UNIQUE PRIMARY KEY,\\n    "name" varchar(20) NOT NULL,\\n    "gender" varchar(1) NOT NULL,\\n    "gender2" varchar(1) NOT NULL\\n)\\n;', 'INSERT INTO "schema_evolution_person" SELECT "id","name","gender","gender2" FROM "schema_evolution_person_1337_TMP";', 'DROP TABLE "schema_evolution_person_1337_TMP";', '-- end warning']
>>> for s in sql: cursor.execute(s).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('select * from "schema_evolution_person";').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.fetchall()[0]
(1, u'2', u'3', u'4')

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# rename column, so it looks like we've recently renamed a field
>>> cursor.execute('DROP TABLE "schema_evolution_person"').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('CREATE TABLE "schema_evolution_person" ("id" integer NOT NULL UNIQUE PRIMARY KEY, "name" varchar(20) NOT NULL, "gender" varchar(1) NOT NULL, "gender_old" varchar(1) NOT NULL );').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute( 'insert into "schema_evolution_person" values (1,2,3,4);' ).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> sql = management.get_sql_evolution(app)
>>> print sql
['-- FYI: sqlite does not support renaming columns, so we create a new "schema_evolution_person" and delete the old  (ie, this could take a while)', 'ALTER TABLE "schema_evolution_person" RENAME TO "schema_evolution_person_1337_TMP";', 'CREATE TABLE "schema_evolution_person" (\\n    "id" integer NOT NULL UNIQUE PRIMARY KEY,\\n    "name" varchar(20) NOT NULL,\\n    "gender" varchar(1) NOT NULL,\\n    "gender2" varchar(1) NOT NULL\\n)\\n;', 'INSERT INTO "schema_evolution_person" SELECT "id","name","gender","gender_old" FROM "schema_evolution_person_1337_TMP";', 'DROP TABLE "schema_evolution_person_1337_TMP";']
>>> for s in sql: cursor.execute(s).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('select * from "schema_evolution_person";').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.fetchall()[0]
(1, u'2', u'3', u'4')

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# rename table, so it looks like we've recently renamed a model
>>> for sql in backend.get_change_table_name_sql( 'schema_evolution_personold', 'schema_evolution_person' ): cursor.execute(sql).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_personold" RENAME TO "schema_evolution_person";']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_personold;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# change column flags, so it looks like we've recently changed a column flag
>>> cursor.execute('DROP TABLE "schema_evolution_person";').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute('CREATE TABLE "schema_evolution_person" ( "id" integer NOT NULL UNIQUE PRIMARY KEY, "name" varchar(20) NOT NULL, "gender" varchar(1) NOT NULL, "gender2" varchar(1) NULL);').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> management.get_sql_evolution(app)
['-- FYI: sqlite does not support changing columns, so we create a new "schema_evolution_person" and delete the old  (ie, this could take a while)', 'ALTER TABLE "schema_evolution_person" RENAME TO "schema_evolution_person_1337_TMP";', 'CREATE TABLE "schema_evolution_person" (\\n    "id" integer NOT NULL UNIQUE PRIMARY KEY,\\n    "name" varchar(20) NOT NULL,\\n    "gender" varchar(1) NOT NULL,\\n    "gender2" varchar(1) NOT NULL\\n)\\n;', 'INSERT INTO "schema_evolution_person" SELECT "id","name","gender","gender2" FROM "schema_evolution_person_1337_TMP";', 'DROP TABLE "schema_evolution_person_1337_TMP";']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_person;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[0]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# delete a datetime column pair, so it looks like we've recently added a datetime field
>>> for sql in ['DROP TABLE schema_evolution_muebles;','CREATE TABLE "schema_evolution_muebles" ("id" integer NOT NULL UNIQUE PRIMARY KEY,"tipo" varchar(40) NOT NULL);']: cursor.execute(sql).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_muebles" ADD COLUMN "fecha_publicacion" datetime NOT NULL;']

# reset the db
>>> cursor.execute('DROP TABLE schema_evolution_muebles;').__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> cursor.execute(create_table_sql[1]).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>

# delete a column with a default value, so it looks like we've recently added a column
>>> for sql in ['DROP TABLE schema_evolution_muebles;','CREATE TABLE "schema_evolution_muebles" ("id" integer NOT NULL UNIQUE PRIMARY KEY,"fecha_publicacion" datetime NOT NULL);']: cursor.execute(sql).__class__
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
<class 'django.db.backends.sqlite3.base.SQLiteCursorWrapper'>
>>> management.get_sql_evolution(app)
['ALTER TABLE "schema_evolution_muebles" ADD COLUMN "tipo" varchar(40) NOT NULL DEFAULT "woot";']

"""

