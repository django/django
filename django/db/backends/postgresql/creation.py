# This dictionary maps Field objects to their associated PostgreSQL column
# types, as strings. Column-type strings can contain format strings; they'll
# be interpolated against the values of Field.__dict__ before being output.
# If a column type is set to None, it won't be included in the output.
DATA_TYPES = {
    'AutoField':         'serial',
    'BooleanField':      'boolean',
    'CharField':         'varchar(%(maxlength)s)',
    'CommaSeparatedIntegerField': 'varchar(%(maxlength)s)',
    'DateField':         'date',
    'DateTimeField':     'timestamp with time zone',
    'FileField':         'varchar(100)',
    'FilePathField':     'varchar(100)',
    'FloatField':        'numeric(%(max_digits)s, %(decimal_places)s)',
    'ImageField':        'varchar(100)',
    'IntegerField':      'integer',
    'IPAddressField':    'inet',
    'NullBooleanField':  'boolean',
    'OneToOneField':     'integer',
    'PhoneNumberField':  'varchar(20)',
    'PositiveIntegerField': 'integer CHECK ("%(column)s" >= 0)',
    'PositiveSmallIntegerField': 'smallint CHECK ("%(column)s" >= 0)',
    'SlugField':         'varchar(%(maxlength)s)',
    'SmallIntegerField': 'smallint',
    'TextField':         'text',
    'TimeField':         'time',
    'USStateField':      'varchar(2)',
    'NoField':           None,
}
