"""
Tests for the file storage mechanism

>>> import tempfile
>>> from django.core.files.storage import FileSystemStorage
>>> from django.core.files.base import ContentFile

>>> temp_storage = FileSystemStorage(location=tempfile.gettempdir())

# Standard file access options are available, and work as expected.

>>> temp_storage.exists('storage_test')
False
>>> file = temp_storage.open('storage_test', 'w')
>>> file.write('storage contents')
>>> file.close()

>>> temp_storage.exists('storage_test')
True
>>> file = temp_storage.open('storage_test', 'r')
>>> file.read()
'storage contents'
>>> file.close()

>>> temp_storage.delete('storage_test')
>>> temp_storage.exists('storage_test')
False

# Files can only be accessed if they're below the specified location.

>>> temp_storage.exists('..')
Traceback (most recent call last):
...
SuspiciousOperation: Attempted access to '..' denied.
>>> temp_storage.open('/etc/passwd')
Traceback (most recent call last):
  ...
SuspiciousOperation: Attempted access to '/etc/passwd' denied.

# Custom storage systems can be created to customize behavior

>>> class CustomStorage(FileSystemStorage):
...     def get_available_name(self, name):
...         # Append numbers to duplicate files rather than underscores, like Trac
...
...         parts = name.split('.')
...         basename, ext = parts[0], parts[1:]
...         number = 2
...
...         while self.exists(name):
...             name = '.'.join([basename, str(number)] + ext)
...             number += 1
...
...         return name
>>> custom_storage = CustomStorage(tempfile.gettempdir())

>>> first = custom_storage.save('custom_storage', ContentFile('custom contents'))
>>> first
u'custom_storage'
>>> second = custom_storage.save('custom_storage', ContentFile('more contents'))
>>> second
u'custom_storage.2'

>>> custom_storage.delete(first)
>>> custom_storage.delete(second)
"""
