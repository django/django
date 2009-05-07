"""
42. Storing files according to a custom storage system

``FileField`` and its variations can take a ``storage`` argument to specify how
and where files should be stored.
"""

import shutil
import tempfile
from django.db import models
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.core.cache import cache

temp_storage_location = tempfile.mkdtemp()
temp_storage = FileSystemStorage(location=temp_storage_location)

# Write out a file to be used as default content
temp_storage.save('tests/default.txt', ContentFile('default content'))

class Storage(models.Model):
    def custom_upload_to(self, filename):
        return 'foo'

    def random_upload_to(self, filename):
        # This returns a different result each time,
        # to make sure it only gets called once.
        import random
        return '%s/%s' % (random.randint(100, 999), filename)

    normal = models.FileField(storage=temp_storage, upload_to='tests')
    custom = models.FileField(storage=temp_storage, upload_to=custom_upload_to)
    random = models.FileField(storage=temp_storage, upload_to=random_upload_to)
    default = models.FileField(storage=temp_storage, upload_to='tests', default='tests/default.txt')

__test__ = {'API_TESTS':"""
# Attempting to access a FileField from the class raises a descriptive error
>>> Storage.normal
Traceback (most recent call last):
...
AttributeError: The 'normal' attribute can only be accessed from Storage instances.

# An object without a file has limited functionality.

>>> obj1 = Storage()
>>> obj1.normal
<FieldFile: None>
>>> obj1.normal.size
Traceback (most recent call last):
...
ValueError: The 'normal' attribute has no file associated with it.

# Saving a file enables full functionality.

>>> obj1.normal.save('django_test.txt', ContentFile('content'))
>>> obj1.normal
<FieldFile: tests/django_test.txt>
>>> obj1.normal.size
7
>>> obj1.normal.read()
'content'

# File objects can be assigned to FileField attributes,  but shouldn't get
# committed until the model it's attached to is saved.

>>> obj1.normal = SimpleUploadedFile('assignment.txt', 'content')
>>> dirs, files = temp_storage.listdir('tests')
>>> dirs
[]
>>> files.sort()
>>> files
['default.txt', 'django_test.txt']

>>> obj1.save()
>>> dirs, files = temp_storage.listdir('tests')
>>> files.sort()
>>> files
['assignment.txt', 'default.txt', 'django_test.txt']

# Files can be read in a little at a time, if necessary.

>>> obj1.normal.open()
>>> obj1.normal.read(3)
'con'
>>> obj1.normal.read()
'tent'
>>> '-'.join(obj1.normal.chunks(chunk_size=2))
'co-nt-en-t'

# Save another file with the same name.

>>> obj2 = Storage()
>>> obj2.normal.save('django_test.txt', ContentFile('more content'))
>>> obj2.normal
<FieldFile: tests/django_test_.txt>
>>> obj2.normal.size
12

# Push the objects into the cache to make sure they pickle properly

>>> cache.set('obj1', obj1)
>>> cache.set('obj2', obj2)
>>> cache.get('obj2').normal
<FieldFile: tests/django_test_.txt>

# Deleting an object deletes the file it uses, if there are no other objects
# still using that file.

>>> obj2.delete()
>>> obj2.normal.save('django_test.txt', ContentFile('more content'))
>>> obj2.normal
<FieldFile: tests/django_test_.txt>

# Default values allow an object to access a single file.

>>> obj3 = Storage.objects.create()
>>> obj3.default
<FieldFile: tests/default.txt>
>>> obj3.default.read()
'default content'

# But it shouldn't be deleted, even if there are no more objects using it.

>>> obj3.delete()
>>> obj3 = Storage()
>>> obj3.default.read()
'default content'

# Verify the fix for #5655, making sure the directory is only determined once.

>>> obj4 = Storage()
>>> obj4.random.save('random_file', ContentFile('random content'))
>>> obj4.random
<FieldFile: .../random_file>

# Clean up the temporary files and dir.
>>> obj1.normal.delete()
>>> obj2.normal.delete()
>>> obj3.default.delete()
>>> obj4.random.delete()
>>> shutil.rmtree(temp_storage_location)
"""}
