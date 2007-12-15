# Test access to max_length while still providing full backwards compatibility
# with legacy maxlength attribute.
"""

Don't print out the deprecation warnings during testing.
>>> from warnings import filterwarnings
>>> filterwarnings("ignore")

# legacy_maxlength function

>>> from django.utils.maxlength import legacy_maxlength

>>> legacy_maxlength(None, None)


>>> legacy_maxlength(10, None)
10

>>> legacy_maxlength(None, 10)
10

>>> legacy_maxlength(10, 12)
Traceback (most recent call last):
...
TypeError: Field cannot take both the max_length argument and the legacy maxlength argument.

>>> legacy_maxlength(0, 10)
Traceback (most recent call last):
...
TypeError: Field cannot take both the max_length argument and the legacy maxlength argument.

>>> legacy_maxlength(0, None)
0

>>> legacy_maxlength(None, 0)
0

#===============================================================================
# Fields
#===============================================================================

# Set up fields
>>> from django.db.models import fields
>>> new = fields.Field(max_length=15)
>>> old = fields.Field(maxlength=10)

# Ensure both max_length and legacy maxlength are not able to both be specified
>>> fields.Field(maxlength=10, max_length=15)
Traceback (most recent call last):
    ...
TypeError: Field cannot take both the max_length argument and the legacy maxlength argument.

# Test max_length
>>> new.max_length
15
>>> old.max_length
10

# Test accessing maxlength
>>> new.maxlength
15
>>> old.maxlength
10

# Test setting maxlength
>>> new.maxlength += 1
>>> old.maxlength += 1
>>> new.max_length
16
>>> old.max_length
11

# SlugField __init__ passes through max_length so test that too
>>> fields.SlugField('new', max_length=15).max_length
15
>>> fields.SlugField('empty').max_length
50
>>> fields.SlugField('old', maxlength=10).max_length
10

#===============================================================================
# (old)forms
#===============================================================================

>>> from django import oldforms

# Test max_length attribute

>>> oldforms.TextField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vTextField" name="new" size="30" value="" maxlength="15" />'

>>> oldforms.IntegerField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vIntegerField" name="new" size="10" value="" maxlength="15" />'

>>> oldforms.SmallIntegerField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vSmallIntegerField" name="new" size="5" value="" maxlength="15" />'

>>> oldforms.PositiveIntegerField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vPositiveIntegerField" name="new" size="10" value="" maxlength="15" />'

>>> oldforms.PositiveSmallIntegerField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vPositiveSmallIntegerField" name="new" size="5" value="" maxlength="15" />'

>>> oldforms.DatetimeField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vDatetimeField" name="new" size="30" value="" maxlength="15" />'

>>> oldforms.EmailField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vEmailField" name="new" size="50" value="" maxlength="15" />'
>>> oldforms.EmailField('new').render('')
u'<input type="text" id="id_new" class="vEmailField" name="new" size="50" value="" maxlength="75" />'

>>> oldforms.URLField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vURLField" name="new" size="50" value="" maxlength="15" />'
>>> oldforms.URLField('new').render('')
u'<input type="text" id="id_new" class="vURLField" name="new" size="50" value="" maxlength="200" />'

>>> oldforms.IPAddressField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vIPAddressField" name="new" size="15" value="" maxlength="15" />'
>>> oldforms.IPAddressField('new').render('')
u'<input type="text" id="id_new" class="vIPAddressField" name="new" size="15" value="" maxlength="15" />'

>>> oldforms.CommaSeparatedIntegerField('new', max_length=15).render('')
u'<input type="text" id="id_new" class="vCommaSeparatedIntegerField" name="new" size="20" value="" maxlength="15" />'


# Test legacy maxlength attribute

>>> oldforms.TextField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vTextField" name="old" size="30" value="" maxlength="10" />'

>>> oldforms.IntegerField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vIntegerField" name="old" size="10" value="" maxlength="10" />'

>>> oldforms.SmallIntegerField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vSmallIntegerField" name="old" size="5" value="" maxlength="10" />'

>>> oldforms.PositiveIntegerField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vPositiveIntegerField" name="old" size="10" value="" maxlength="10" />'

>>> oldforms.PositiveSmallIntegerField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vPositiveSmallIntegerField" name="old" size="5" value="" maxlength="10" />'

>>> oldforms.DatetimeField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vDatetimeField" name="old" size="30" value="" maxlength="10" />'

>>> oldforms.EmailField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vEmailField" name="old" size="50" value="" maxlength="10" />'

>>> oldforms.URLField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vURLField" name="old" size="50" value="" maxlength="10" />'

>>> oldforms.IPAddressField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vIPAddressField" name="old" size="15" value="" maxlength="10" />'

>>> oldforms.CommaSeparatedIntegerField('old', maxlength=10).render('')
u'<input type="text" id="id_old" class="vCommaSeparatedIntegerField" name="old" size="20" value="" maxlength="10" />'
"""
if __name__ == "__main__":
    import doctest
    doctest.testmod()
