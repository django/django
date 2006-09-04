"""
>>> from django.db.backends.ansi import sql

# so we can test with a predicatable constraint setting
>>> real_cnst = Mod._default_manager.db.backend.supports_constraints
>>> Mod._default_manager.db.backend.supports_constraints = True
    
# generate create sql
>>> builder = sql.SchemaBuilder()
>>> builder.get_create_table(Car)
([BoundStatement('CREATE TABLE "ansi_sql_car" (...);')], {})
>>> builder.models_already_seen
Set([<class 'regressiontests.ansi_sql.models.Car'>])
>>> builder.models_already_seen = set()

# test that styles are used
>>> builder.get_create_table(Car, style=mockstyle())
([BoundStatement('SQL_KEYWORD(CREATE TABLE) SQL_TABLE("ansi_sql_car") (...SQL_FIELD("id")...);')], {})

# test pending relationships
>>> builder.models_already_seen = set()
>>> builder.get_create_table(Mod)
([BoundStatement('CREATE TABLE "ansi_sql_mod" (..."car_id" integer NOT NULL,...);')], {<class 'regressiontests.ansi_sql.models.Car'>: [BoundStatement('ALTER TABLE "ansi_sql_mod" ADD CONSTRAINT ... FOREIGN KEY ("car_id") REFERENCES "ansi_sql_car" ("id");')]})
>>> builder.models_already_seen = set()
>>> builder.get_create_table(Car)
([BoundStatement('CREATE TABLE "ansi_sql_car" (...);')], {})
>>> builder.get_create_table(Mod)
([BoundStatement('CREATE TABLE "ansi_sql_mod" (..."car_id" integer NOT NULL REFERENCES "ansi_sql_car" ("id"),...);')], {})

# test many-many
>>> builder.get_create_table(Collector)
([BoundStatement('CREATE TABLE "ansi_sql_collector" (...);')], {})
>>> builder.get_create_many_to_many(Collector)
{<class 'regressiontests.ansi_sql.models.Car'>: [BoundStatement('CREATE TABLE "ansi_sql_collector_cars" (...);')]}

# test indexes
>>> builder.get_create_indexes(Car)
[]
>>> builder.get_create_indexes(Mod)
[BoundStatement('CREATE INDEX ... ON "ansi_sql_mod" ("car_id");'), BoundStatement('CREATE INDEX ... ON "ansi_sql_mod" ("part");')]
>>> builder.get_create_indexes(Collector)
[]

# test initial data
# patch builder so that it looks for initial data where we want it to
# >>> builder.get_initialdata_path = othertests_sql
>>> builder.get_initialdata(Car)
[BoundStatement('insert into ansi_sql_car (...)...values (...);')]

# test drop
>>> builder.get_drop_table(Mod)
[BoundStatement('DROP TABLE "ansi_sql_mod";')]
>>> builder.get_drop_table(Mod, cascade=True)
[BoundStatement('DROP TABLE "ansi_sql_mod";')]
>>> builder.get_drop_table(Car)
[BoundStatement('DROP TABLE "ansi_sql_car";')]

# drop with cascade
>>> builder.tables = ['ansi_sql_car', 'ansi_sql_mod', 'ansi_sql_collector']
>>> Mod._default_manager.db.backend.supports_constraints = False
>>> Mod._default_manager.db.backend.supports_constraints
False
>>> Car._default_manager.db.backend.supports_constraints
False
>>> builder.get_drop_table(Car, cascade=True)
[BoundStatement('DROP TABLE "ansi_sql_car";')]
>>> Mod._default_manager.db.backend.supports_constraints = True
>>> Mod._default_manager.db.backend.supports_constraints
True
>>> Car._default_manager.db.backend.supports_constraints
True
>>> builder.get_drop_table(Car, cascade=True)
[BoundStatement('DROP TABLE "ansi_sql_car";'), BoundStatement('ALTER TABLE "ansi_sql_mod" ...')]
>>> builder.get_drop_table(Collector)
[BoundStatement('DROP TABLE "ansi_sql_collector";')]
>>> builder.get_drop_table(Collector, cascade=True)
[BoundStatement('DROP TABLE "ansi_sql_collector";'), BoundStatement('DROP TABLE "ansi_sql_collector_cars";')]
>>> Mod._default_manager.db.backend.supports_constraints = real_cnst

"""
#import os
#import sys
#from django.conf import settings
#from django.core.management import install
from django.db import models
#from django.db.models import loading


# For Python 2.3
if not hasattr(__builtins__, 'set'):
    from sets import Set as set


# test models
class Car(models.Model):
    make = models.CharField(maxlength=32)
    model = models.CharField(maxlength=32)
    year = models.IntegerField()
    condition = models.CharField(maxlength=32)

        
class Collector(models.Model):
    name = models.CharField(maxlength=32)
    cars = models.ManyToManyField(Car)

        
class Mod(models.Model):
    car = models.ForeignKey(Car)
    part = models.CharField(maxlength=32, db_index=True)
    description = models.TextField()


class mockstyle:
    """mock style that wraps text in STYLE(text), for testing"""
    def __getattr__(self, attr):
        if attr in ('ERROR', 'ERROR_OUTPUT', 'SQL_FIELD', 'SQL_COLTYPE',
                    'SQL_KEYWORD', 'SQL_TABLE'):
            return lambda text: "%s(%s)" % (attr, text)

        
# def othertests_sql(mod):
#     """Look in othertests/sql for sql initialdata"""
#     return os.path.normpath(os.path.join(os.path.dirname(__file__), 'sql'))


# # install my models and force myself into the registry of apps and models
# # (without this, references and such to/from the models installed here
# # won't be picked up in get_models(), since get_models() looks only at
# # models from apps in INSTALLED_APPS, and the model and app lookup rules
# # enforce a module structure that this test file can't follow)
# Car.objects.install()
# Collector.objects.install()
# Mod.objects.install()
# loading.get_apps()
# loading._app_list.append(sys.modules[__name__])

# # model lookup only works for pk.models, so fake up my module name
# __name__ = 'othertests.ansi_sql.models'
