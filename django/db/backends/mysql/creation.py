# This dictionary maps Field objects to their associated MySQL column
# types, as strings. Column-type strings can contain format strings; they'll
# be interpolated against the values of Field.__dict__ before being output.
# If a column type is set to None, it won't be included in the output.
DATA_TYPES = {
    'AutoField':         'integer AUTO_INCREMENT',
    'BooleanField':      'bool',
    'CharField':         'varchar(%(max_length)s)',
    'CommaSeparatedIntegerField': 'varchar(%(max_length)s)',
    'DateField':         'date',
    'DateTimeField':     'datetime',
    'DecimalField':      'numeric(%(max_digits)s, %(decimal_places)s)',
    'FileField':         'varchar(%(max_length)s)',
    'FilePathField':     'varchar(%(max_length)s)',
    'FloatField':        'double precision',
    'IntegerField':      'integer',
    'IPAddressField':    'char(15)',
    'NullBooleanField':  'bool',
    'OneToOneField':     'integer',
    'PhoneNumberField':  'varchar(20)',
    'PositiveIntegerField': 'integer UNSIGNED',
    'PositiveSmallIntegerField': 'smallint UNSIGNED',
    'SlugField':         'varchar(%(max_length)s)',
    'SmallIntegerField': 'smallint',
    'TextField':         'longtext',
    'TimeField':         'time',
    'USStateField':      'varchar(2)',
}
