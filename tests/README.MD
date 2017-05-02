# Setting up Postgres for testing

1. install postgres through http://postgresapp.com/
1. start postgres shell
1. `CREATE ROLE [role name] WITH LOGIN`
1. `CREATE DATABASE [database name]`
1. set the following values under `DATABASE` for both `default` and `other`:
```
'NAME': 'django_test_db',                      
'USER': 'czhang',
'PASSWORD': 'password', # the value doesn't matter
'HOST': 'localhost',
```
1. go to [repo root folder]/tests
1. run `runtests.py --settings=test_postgres postgres_tests`
