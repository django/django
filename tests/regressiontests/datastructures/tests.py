"""
# Tests for stuff in django.utils.datastructures.

>>> from django.utils.datastructures import *

### MergeDict #################################################################

>>> d1 = {'chris':'cool','camri':'cute','cotton':'adorable','tulip':'snuggable', 'twoofme':'firstone'}
>>> d2 = {'chris2':'cool2','camri2':'cute2','cotton2':'adorable2','tulip2':'snuggable2'}
>>> d3 = {'chris3':'cool3','camri3':'cute3','cotton3':'adorable3','tulip3':'snuggable3'}
>>> d4 = {'twoofme':'secondone'}
>>> md = MergeDict( d1,d2,d3 )
>>> md['chris']
'cool'
>>> md['camri']
'cute'
>>> md['twoofme']
'firstone'
>>> md2 = md.copy()
>>> md2['chris']
'cool'

### MultiValueDict ##########################################################

>>> d = MultiValueDict({'name': ['Adrian', 'Simon'], 'position': ['Developer']})
>>> d['name']
'Simon'
>>> d.getlist('name')
['Adrian', 'Simon']
>>> d.get('lastname', 'nonexistent')
'nonexistent'
>>> d.setlist('lastname', ['Holovaty', 'Willison'])

"""