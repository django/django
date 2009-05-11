import copy
import datetime
import os

from django.conf import settings
from django.db.models.fields import Field
from django.core.files.base import File, ContentFile
from django.core.files.storage import default_storage
from django.core.files.images import ImageFile, get_image_dimensions
from django.core.files.uploadedfile import UploadedFile
from django.utils.functional import curry
from django.db.models import signals
from django.utils.encoding import force_unicode, smart_str
from django.utils.translation import ugettext_lazy, ugettext as _
from django import forms
from django.db.models.loading import cache

class FieldFile(File):
    def __init__(self, instance, field, name):
        super(FieldFile, self).__init__(None, name)
        self.instance = instance
        self.field = field
        self.storage = field.storage
        self._committed = True

    def __eq__(self, other):
        # Older code may be expecting FileField values to be simple strings.
        # By overriding the == operator, it can remain backwards compatibility.
        if hasattr(other, 'name'):
            return self.name == other.name
        return self.name == other

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        # Required because we defined a custom __eq__.
        return hash(self.name)

    # The standard File contains most of the necessary properties, but
    # FieldFiles can be instantiated without a name, so that needs to
    # be checked for here.

    def _require_file(self):
        if not self:
            raise ValueError("The '%s' attribute has no file associated with it." % self.field.name)

    def _get_file(self):
        self._require_file()
        if not hasattr(self, '_file') or self._file is None:
            self._file = self.storage.open(self.name, 'rb')
        return self._file

    def _set_file(self, file):
        self._file = file

    def _del_file(self):
        del self._file

    file = property(_get_file, _set_file, _del_file)

    def _get_path(self):
        self._require_file()
        return self.storage.path(self.name)
    path = property(_get_path)

    def _get_url(self):
        self._require_file()
        return self.storage.url(self.name)
    url = property(_get_url)

    def _get_size(self):
        self._require_file()
        if not self._committed:
            return len(self.file)
        return self.storage.size(self.name)
    size = property(_get_size)

    def open(self, mode='rb'):
        self._require_file()
        self.file.open(mode)
    # open() doesn't alter the file's contents, but it does reset the pointer
    open.alters_data = True

    # In addition to the standard File API, FieldFiles have extra methods
    # to further manipulate the underlying file, as well as update the
    # associated model instance.

    def save(self, name, content, save=True):
        name = self.field.generate_filename(self.instance, name)
        self.name = self.storage.save(name, content)
        setattr(self.instance, self.field.name, self.name)

        # Update the filesize cache
        self._size = len(content)
        self._committed = True

        # Save the object because it has changed, unless save is False
        if save:
            self.instance.save()
    save.alters_data = True

    def delete(self, save=True):
        # Only close the file if it's already open, which we know by the
        # presence of self._file
        if hasattr(self, '_file'):
            self.close()
            del self.file

        self.storage.delete(self.name)

        self.name = None
        setattr(self.instance, self.field.name, self.name)

        # Delete the filesize cache
        if hasattr(self, '_size'):
            del self._size
        self._committed = False

        if save:
            self.instance.save()
    delete.alters_data = True

    def _get_closed(self):
        file = getattr(self, '_file', None)
        return file is None or file.closed
    closed = property(_get_closed)

    def close(self):
        file = getattr(self, '_file', None)
        if file is not None:
            file.close()

    def __getstate__(self):
        # FieldFile needs access to its associated model field and an instance
        # it's attached to in order to work properly, but the only necessary
        # data to be pickled is the file's name itself. Everything else will
        # be restored later, by FileDescriptor below.
        return {'name': self.name, 'closed': False, '_committed': True, '_file': None}

class FileDescriptor(object):
    """
    The descriptor for the file attribute on the model instance. Returns a
    FieldFile when accessed so you can do stuff like::
    
        >>> instance.file.size
        
    Assigns a file object on assignment so you can do::
    
        >>> instance.file = File(...)
        
    """
    def __init__(self, field):
        self.field = field

    def __get__(self, instance=None, owner=None):
        if instance is None:
            raise AttributeError(
                "The '%s' attribute can only be accessed from %s instances." 
                % (self.field.name, owner.__name__))
                
        # This is slightly complicated, so worth an explanation.
        # instance.file`needs to ultimately return some instance of `File`,
        # probably a subclass. Additionally, this returned object needs to have
        # the FieldFile API so that users can easily do things like
        # instance.file.path and have that delegated to the file storage engine.
        # Easy enough if we're strict about assignment in __set__, but if you
        # peek below you can see that we're not. So depending on the current
        # value of the field we have to dynamically construct some sort of
        # "thing" to return.
        
        # The instance dict contains whatever was originally assigned 
        # in __set__.
        file = instance.__dict__[self.field.name]

        # If this value is a string (instance.file = "path/to/file") or None
        # then we simply wrap it with the appropriate attribute class according
        # to the file field. [This is FieldFile for FileFields and
        # ImageFieldFile for ImageFields; it's also conceivable that user
        # subclasses might also want to subclass the attribute class]. This
        # object understands how to convert a path to a file, and also how to
        # handle None.
        if isinstance(file, basestring) or file is None:
            attr = self.field.attr_class(instance, self.field, file)
            instance.__dict__[self.field.name] = attr

        # Other types of files may be assigned as well, but they need to have
        # the FieldFile interface added to the. Thus, we wrap any other type of
        # File inside a FieldFile (well, the field's attr_class, which is 
        # usually FieldFile).
        elif isinstance(file, File) and not isinstance(file, FieldFile):
            file_copy = self.field.attr_class(instance, self.field, file.name)
            file_copy.file = file
            file_copy._committed = False
            instance.__dict__[self.field.name] = file_copy
            
        # Finally, because of the (some would say boneheaded) way pickle works,
        # the underlying FieldFile might not actually itself have an associated
        # file. So we need to reset the details of the FieldFile in those cases.
        elif isinstance(file, FieldFile) and not hasattr(file, 'field'):
            file.instance = instance
            file.field = self.field
            file.storage = self.field.storage
        
        # That was fun, wasn't it?
        return instance.__dict__[self.field.name]

    def __set__(self, instance, value):
        instance.__dict__[self.field.name] = value

class FileField(Field):
    # The class to wrap instance attributes in. Accessing the file object off
    # the instance will always return an instance of attr_class.
    attr_class = FieldFile
    
    # The descriptor to use for accessing the attribute off of the class.
    descriptor_class = FileDescriptor

    def __init__(self, verbose_name=None, name=None, upload_to='', storage=None, **kwargs):
        for arg in ('primary_key', 'unique'):
            if arg in kwargs:
                raise TypeError("'%s' is not a valid argument for %s." % (arg, self.__class__))

        self.storage = storage or default_storage
        self.upload_to = upload_to
        if callable(upload_to):
            self.generate_filename = upload_to

        kwargs['max_length'] = kwargs.get('max_length', 100)
        super(FileField, self).__init__(verbose_name, name, **kwargs)

    def get_internal_type(self):
        return "FileField"

    def get_db_prep_lookup(self, lookup_type, value):
        if hasattr(value, 'name'):
            value = value.name
        return super(FileField, self).get_db_prep_lookup(lookup_type, value)

    def get_db_prep_value(self, value):
        "Returns field's value prepared for saving into a database."
        # Need to convert File objects provided via a form to unicode for database insertion
        if value is None:
            return None
        return unicode(value)

    def pre_save(self, model_instance, add):
        "Returns field's value just before saving."
        file = super(FileField, self).pre_save(model_instance, add)
        if file and not file._committed:
            # Commit the file to storage prior to saving the model
            file.save(file.name, file, save=False)
        return file

    def contribute_to_class(self, cls, name):
        super(FileField, self).contribute_to_class(cls, name)
        setattr(cls, self.name, self.descriptor_class(self))
        signals.post_delete.connect(self.delete_file, sender=cls)

    def delete_file(self, instance, sender, **kwargs):
        file = getattr(instance, self.attname)
        # If no other object of this type references the file,
        # and it's not the default value for future objects,
        # delete it from the backend.
        if file and file.name != self.default and \
            not sender._default_manager.filter(**{self.name: file.name}):
                file.delete(save=False)
        elif file:
            # Otherwise, just close the file, so it doesn't tie up resources.
            file.close()

    def get_directory_name(self):
        return os.path.normpath(force_unicode(datetime.datetime.now().strftime(smart_str(self.upload_to))))

    def get_filename(self, filename):
        return os.path.normpath(self.storage.get_valid_name(os.path.basename(filename)))

    def generate_filename(self, instance, filename):
        return os.path.join(self.get_directory_name(), self.get_filename(filename))

    def save_form_data(self, instance, data):
        if data:
            setattr(instance, self.name, data)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.FileField, 'max_length': self.max_length}
        # If a file has been provided previously, then the form doesn't require
        # that a new file is provided this time.
        # The code to mark the form field as not required is used by
        # form_for_instance, but can probably be removed once form_for_instance
        # is gone. ModelForm uses a different method to check for an existing file.
        if 'initial' in kwargs:
            defaults['required'] = False
        defaults.update(kwargs)
        return super(FileField, self).formfield(**defaults)

class ImageFileDescriptor(FileDescriptor):
    """
    Just like the FileDescriptor, but for ImageFields. The only difference is
    assigning the width/height to the width_field/height_field, if appropriate.
    """
    def __set__(self, instance, value):
        super(ImageFileDescriptor, self).__set__(instance, value)
        
        # The rest of this method deals with width/height fields, so we can
        # bail early if neither is used.
        if not self.field.width_field and not self.field.height_field:
            return
        
        # We need to call the descriptor's __get__ to coerce this assigned 
        # value into an instance of the right type (an ImageFieldFile, in this
        # case).
        value = self.__get__(instance)
        
        if not value:
            return
        
        # Get the image dimensions, making sure to leave the file in the same
        # state (opened or closed) that we got it in. However, we *don't* rewind
        # the file pointer if the file is already open. This is in keeping with
        # most Python standard library file operations that leave it up to the
        # user code to reset file pointers after operations that move it.
        from django.core.files.images import get_image_dimensions
        close = value.closed
        value.open()
        try:
            width, height = get_image_dimensions(value)
        finally:
            if close:
                value.close()
        
        # Update the width and height fields
        if self.field.width_field:
            setattr(value.instance, self.field.width_field, width)
        if self.field.height_field:
            setattr(value.instance, self.field.height_field, height)

class ImageFieldFile(ImageFile, FieldFile):
    def delete(self, save=True):
        # Clear the image dimensions cache
        if hasattr(self, '_dimensions_cache'):
            del self._dimensions_cache
        super(ImageFieldFile, self).delete(save)

class ImageField(FileField):
    attr_class = ImageFieldFile
    descriptor_class = ImageFileDescriptor

    def __init__(self, verbose_name=None, name=None, width_field=None, height_field=None, **kwargs):
        self.width_field, self.height_field = width_field, height_field
        FileField.__init__(self, verbose_name, name, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.ImageField}
        defaults.update(kwargs)
        return super(ImageField, self).formfield(**defaults)
