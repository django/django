# SQLite doesn't actually support most of these types, but it "does the right
# thing" given more verbose field definitions, so leave them as is so that
# schema inspection is more useful.
DATA_TYPES = {
    'AutoField':                    'integer',
    'BooleanField':                 'bool',
    'CharField':                    'varchar(%(maxlength)s)',
    'CommaSeparatedIntegerField':   'varchar(%(maxlength)s)',
    'DateField':                    'date',
    'DateTimeField':                'datetime',
    'FileField':                    'varchar(100)',
    'FilePathField':                'varchar(100)',
    'FloatField':                   'numeric(%(max_digits)s, %(decimal_places)s)',
    'ImageField':                   'varchar(100)',
    'IntegerField':                 'integer',
    'IPAddressField':               'char(15)',
    'ManyToManyField':              None,
    'NullBooleanField':             'bool',
    'OneToOneField':                'integer',
    'PhoneNumberField':             'varchar(20)',
    'PositiveIntegerField':         'integer unsigned',
    'PositiveSmallIntegerField':    'smallint unsigned',
    'SlugField':                    'varchar(%(maxlength)s)',
    'SmallIntegerField':            'smallint',
    'TextField':                    'text',
    'TimeField':                    'time',
    'URLField':                     'varchar(200)',
    'USStateField':                 'varchar(2)',
}
