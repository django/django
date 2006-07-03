"""
>>> from django.db import models
>>> from django.db.backends.ansi import sql

# test models
>>> class Car(models.Model):
...     make = models.CharField(maxlength=32)
...     model = models.CharField(maxlength=32)
...     year = models.IntegerField()
...     condition = models.CharField(maxlength=32)
...     
...     class Meta:
...         app_label = 'ansi_sql'

>>> class Collector(models.Model):
...     name = models.CharField(maxlength=32)
...     cars = models.ManyToManyField(Car)
...     
...     class Meta:
...         app_label = 'ansi_sql'

>>> class Mod(models.Model):
...     car = models.ForeignKey(Car)
...     part = models.CharField(maxlength=32, db_index=True)
...     description = models.TextField()
...     
...     class Meta:
...         app_label = 'ansi_sql'
    
# generate create sql
>>> builder = sql.SchemaBuilder()
>>> builder.get_create_table(Car)
([BoundStatement('CREATE TABLE "ansi_sql_car" (...);')], [])
>>> builder.models_already_seen
[<class 'othertests.ansi_sql.Car'>]
>>> builder.models_already_seen = []

# test that styles are used
>>> builder.get_create_table(Car, style=mockstyle())
([BoundStatement('SQL_KEYWORD(CREATE TABLE) SQL_TABLE("ansi_sql_car") (...SQL_FIELD("id")...);')], [])

# test pending relationships
>>> builder.models_already_seen = []
>>> real_cnst = Mod._meta.connection_info.backend.supports_constraints
>>> Mod._meta.connection_info.backend.supports_constraints = True
>>> builder.get_create_table(Mod)
([BoundStatement('CREATE TABLE "ansi_sql_mod" (..."car_id" integer NOT NULL,...);')], [BoundStatement('ALTER TABLE "ansi_sql_mod" ADD CONSTRAINT ... FOREIGN KEY ("car_id") REFERENCES "ansi_sql_car" ("id");')])
>>> builder.models_already_seen = []
>>> builder.get_create_table(Car)
([BoundStatement('CREATE TABLE "ansi_sql_car" (...);')], [])
>>> builder.get_create_table(Mod)
([BoundStatement('CREATE TABLE "ansi_sql_mod" (..."car_id" integer NOT NULL REFERENCES "ansi_sql_car" ("id"),...);')], [])
>>> Mod._meta.connection_info.backend.supports_constraints = real_cnst

# test many-many
>>> builder.get_create_table(Collector)
([BoundStatement('CREATE TABLE "ansi_sql_collector" (...);')], [])
>>> builder.get_create_many_to_many(Collector)
[BoundStatement('CREATE TABLE "ansi_sql_collector_cars" (...);')]

# test indexes
>>> builder.get_create_indexes(Car)
[]
>>> builder.get_create_indexes(Mod)
[BoundStatement('CREATE INDEX ... ON "ansi_sql_mod" ("car_id");'), BoundStatement('CREATE INDEX ... ON "ansi_sql_mod" ("part");')]
>>> builder.get_create_indexes(Collector)
[]

# test initial data
# patch builder so that it looks for initial data where we want it to
>>> builder.get_initialdata_path = othertests_sql
>>> builder.get_initialdata(Car)
[BoundStatement('insert into ansi_sql_car (...)...values (...);')]
"""
import os

# mock style that wraps text in STYLE(text), for testing
class mockstyle:
    def __getattr__(self, attr):
        if attr in ('ERROR', 'ERROR_OUTPUT', 'SQL_FIELD', 'SQL_COLTYPE',
                    'SQL_KEYWORD', 'SQL_TABLE'):
            return lambda text: "%s(%s)" % (attr, text)

def othertests_sql(mod):
    """Look in othertests/sql for sql initialdata"""
    return os.path.normpath(os.path.join(os.path.dirname(__file__), 'sql'))
