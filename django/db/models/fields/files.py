import datetime
import posixpath

from django import forms
from django.core import checks
from django.core.exceptions import FieldError
from django.core.files.base import ContentFile, File
from django.core.files.images import ImageFile
from django.core.files.storage import Storage, default_storage
from django.core.files.utils import validate_file_name
from django.db.models import signals
from django.db.models.expressions import DatabaseDefault
from django.db.models.fields import Field
from django.db.models.query_utils import DeferredAttribute
from django.db.models.utils import AltersData
from django.utils.translation import gettext_lazy as _


class FieldFile(File, AltersData):
    def __init__(self, instance, field, name):
        super().__init__(None, name)
        self.instance = instance
        self.field = field
        self.storage = field.storage
        self._committed = True

    def __eq__(self, other):
        # Older code may be expecting FileField values to be simple strings.
        # By overriding the == operator, it can remain backwards compatibility.
        if hasattr(other, "name"):
            return self.name == other.name
        return self.name == other

    def __hash__(self):
        return hash(self.name)

    # The standard File contains most of the necessary properties, but
    # FieldFiles can be instantiated without a name, so that needs to
    # be checked for here.

    def _require_file(self):
        if not self:
            raise ValueError(
                "The '%s' attribute has no file associated with it." % self.field.name
            )

    def _get_file(self):
        self._require_file()
        if getattr(self, "_file", None) is None:
            self._file = self.storage.open(self.name, "rb")
        return self._file

    def _set_file(self, file):
        self._file = file

    def _del_file(self):
        del self._file

    file = property(_get_file, _set_file, _del_file)

    @property
    def path(self):
        self._require_file()
        return self.storage.path(self.name)

    @property
    def url(self):
        self._require_file()
        return self.storage.url(self.name)

    @property
    def size(self):
        self._require_file()
        if not self._committed:
            return self.file.size
        return self.storage.size(self.name)

    def open(self, mode="rb"):
        self._require_file()
        if getattr(self, "_file", None) is None:
            self.file = self.storage.open(self.name, mode)
        else:
            self.file.open(mode)
        return self

    # open() doesn't alter the file's contents, but it does reset the pointer
    open.alters_data = True

    # In addition to the standard File API, FieldFiles have extra methods
    # to further manipulate the underlying file, as well as update the
    # associated model instance.

    def _set_instance_attribute(self, name, content):
        setattr(self.instance, self.field.attname, name)

    def save(self, name, content, save=True):
        name = self.field.generate_filename(self.instance, name)
        self.name = self.storage.save(name, content, max_length=self.field.max_length)
        self._set_instance_attribute(self.name, content)
        self._committed = True

        # Save the object because it has changed, unless save is False
        if save:
            self.instance.save()

    save.alters_data = True

    def delete(self, save=True):
        if not self:
            return
        # Only close the file if it's already open, which we know by the
        # presence of self._file
        if hasattr(self, "_file"):
            self.close()
            del self.file

        self.storage.delete(self.name)

        self.name = None
        setattr(self.instance, self.field.attname, self.name)
        self._committed = False

        if save:
            self.instance.save()

    delete.alters_data = True

    @property
    def closed(self):
        file = getattr(self, "_file", None)
        return file is None or file.closed

    def close(self):
        file = getattr(self, "_file", None)
        if file is not None:
            file.close()

    def __getstate__(self):
        # FieldFile needs access to its associated model field, an instance and
        # the file's name. Everything else will be restored later, by
        # FileDescriptor below.
        return {
            "name": self.name,
            "closed": False,
            "_committed": True,
            "_file": None,
            "instance": self.instance,
            "field": self.field,
        }

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.storage = self.field.storage


class FileDescriptor(DeferredAttribute):
    """
    The descriptor for the file attribute on the model instance. Return a
    FieldFile when accessed so you can write code like::

        >>> from myapp.models import MyModel
        >>> instance = MyModel.objects.get(pk=1)
        >>> instance.file.size

    Assign a file object on assignment so you can do::

        >>> with open('/path/to/hello.world') as f:
        ...     instance.file = File(f)
    """

    def __get__(self, instance, cls=None):
        if instance is None:
            return self

        # This is slightly complicated, so worth an explanation.
        # instance.file needs to ultimately return some instance of `File`,
        # probably a subclass. Additionally, this returned object needs to have
        # the FieldFile API so that users can easily do things like
        # instance.file.path and have that delegated to the file storage engine.
        # Easy enough if we're strict about assignment in __set__, but if you
        # peek below you can see that we're not. So depending on the current
        # value of the field we have to dynamically construct some sort of
        # "thing" to return.

        # The instance dict contains whatever was originally assigned
        # in __set__.
        file = super().__get__(instance, cls)

        # If this value is a string (instance.file = "path/to/file") or None
        # then we simply wrap it with the appropriate attribute class according
        # to the file field. [This is FieldFile for FileFields and
        # ImageFieldFile for ImageFields; it's also conceivable that user
        # subclasses might also want to subclass the attribute class]. This
        # object understands how to convert a path to a file, and also how to
        # handle None.
        if isinstance(file, str) or file is None:
            attr = self.field.attr_class(instance, self.field, file)
            instance.__dict__[self.field.attname] = attr

        # If this value is a DatabaseDefault, initialize the attribute class
        # for this field with its db_default value.
        elif isinstance(file, DatabaseDefault):
            attr = self.field.attr_class(instance, self.field, self.field.db_default)
            instance.__dict__[self.field.attname] = attr

        # Other types of files may be assigned as well, but they need to have
        # the FieldFile interface added to them. Thus, we wrap any other type of
        # File inside a FieldFile (well, the field's attr_class, which is
        # usually FieldFile).
        elif isinstance(file, File) and not isinstance(file, FieldFile):
            file_copy = self.field.attr_class(instance, self.field, file.name)
            file_copy.file = file
            file_copy._committed = False
            instance.__dict__[self.field.attname] = file_copy

        # Finally, because of the (some would say boneheaded) way pickle works,
        # the underlying FieldFile might not actually itself have an associated
        # file. So we need to reset the details of the FieldFile in those cases.
        elif isinstance(file, FieldFile) and not hasattr(file, "field"):
            file.instance = instance
            file.field = self.field
            file.storage = self.field.storage

        # Make sure that the instance is correct.
        elif isinstance(file, FieldFile) and instance is not file.instance:
            file.instance = instance

        # That was fun, wasn't it?
        return instance.__dict__[self.field.attname]

    def __set__(self, instance, value):
        instance.__dict__[self.field.attname] = value


class FileField(Field):
    # The class to wrap instance attributes in. Accessing the file object off
    # the instance will always return an instance of attr_class.
    attr_class = FieldFile

    # The descriptor to use for accessing the attribute off of the class.
    descriptor_class = FileDescriptor

    description = _("File")

    def __init__(
        self, verbose_name=None, name=None, upload_to="", storage=None, **kwargs
    ):
        self._primary_key_set_explicitly = "primary_key" in kwargs

        self.storage = storage or default_storage
        if callable(self.storage):
            # Hold a reference to the callable for deconstruct().
            self._storage_callable = self.storage
            self.storage = self.storage()
            if not isinstance(self.storage, Storage):
                raise TypeError(
                    "%s.storage must be a subclass/instance of %s.%s"
                    % (
                        self.__class__.__qualname__,
                        Storage.__module__,
                        Storage.__qualname__,
                    )
                )
        self.upload_to = upload_to

        kwargs.setdefault("max_length", 100)
        super().__init__(verbose_name, name, **kwargs)

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_primary_key(),
            *self._check_upload_to(),
        ]

    def _check_primary_key(self):
        if self._primary_key_set_explicitly:
            return [
                checks.Error(
                    "'primary_key' is not a valid argument for a %s."
                    % self.__class__.__name__,
                    obj=self,
                    id="fields.E201",
                )
            ]
        else:
            return []

    def _check_upload_to(self):
        if isinstance(self.upload_to, str) and self.upload_to.startswith("/"):
            return [
                checks.Error(
                    "%s's 'upload_to' argument must be a relative path, not an "
                    "absolute path." % self.__class__.__name__,
                    obj=self,
                    id="fields.E202",
                    hint="Remove the leading slash.",
                )
            ]
        else:
            return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if kwargs.get("max_length") == 100:
            del kwargs["max_length"]
        kwargs["upload_to"] = self.upload_to
        storage = getattr(self, "_storage_callable", self.storage)
        if storage is not default_storage:
            kwargs["storage"] = storage
        return name, path, args, kwargs

    def get_internal_type(self):
        return "FileField"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        # Need to convert File objects provided via a form to string for
        # database insertion.
        if value is None:
            return None
        return str(value)

    def pre_save(self, model_instance, add):
        file = super().pre_save(model_instance, add)
        if file.name is None and file._file is not None:
            exc = FieldError(
                f"File for {self.name} must have "
                "the name attribute specified to be saved."
            )
            if isinstance(file._file, ContentFile):
                exc.add_note("Pass a 'name' argument to ContentFile.")
            raise exc

        if file and not file._committed:
            # Commit the file to storage prior to saving the model
            file.save(file.name, file.file, save=False)
        return file

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        setattr(cls, self.attname, self.descriptor_class(self))

    def generate_filename(self, instance, filename):
        """
        Apply (if callable) or prepend (if a string) upload_to to the filename,
        then delegate further processing of the name to the storage backend.
        Until the storage layer, all file paths are expected to be Unix style
        (with forward slashes).
        """
        if callable(self.upload_to):
            filename = self.upload_to(instance, filename)
        else:
            dirname = datetime.datetime.now().strftime(str(self.upload_to))
            filename = posixpath.join(dirname, filename)
        filename = validate_file_name(filename, allow_relative_path=True)
        return self.storage.generate_filename(filename)

    def save_form_data(self, instance, data):
        # Important: None means "no change", other false value means "clear"
        # This subtle distinction (rather than a more explicit marker) is
        # needed because we need to consume values that are also sane for a
        # regular (non Model-) Form to find in its cleaned_data dictionary.
        if data is not None:
            # This value will be converted to str and stored in the
            # database, so leaving False as-is is not acceptable.
            setattr(instance, self.name, data or "")

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": forms.FileField,
                "max_length": self.max_length,
                **kwargs,
            }
        )


class ImageFileDescriptor(FileDescriptor):
    """
    Just like the FileDescriptor, but for ImageFields. The only difference is
    assigning the width/height to the width_field/height_field, if appropriate.
    """

    def __set__(self, instance, value):
        previous_file = instance.__dict__.get(self.field.attname)
        super().__set__(instance, value)

        # To prevent recalculating image dimensions when we are instantiating
        # an object from the database (bug #11084), only update dimensions if
        # the field had a value before this assignment.  Since the default
        # value for FileField subclasses is an instance of field.attr_class,
        # previous_file will only be None when we are called from
        # Model.__init__().  The ImageField.update_dimension_fields method
        # hooked up to the post_init signal handles the Model.__init__() cases.
        # Assignment happening outside of Model.__init__() will trigger the
        # update right here.
        if previous_file is not None:
            self.field.update_dimension_fields(instance, force=True)


class ImageFieldFile(ImageFile, FieldFile):
    def _set_instance_attribute(self, name, content):
        setattr(self.instance, self.field.attname, content)
        # Update the name in case generate_filename() or storage.save() changed
        # it, but bypass the descriptor to avoid re-reading the file.
        self.instance.__dict__[self.field.attname] = self.name

    def delete(self, save=True):
        # Clear the image dimensions cache
        if hasattr(self, "_dimensions_cache"):
            del self._dimensions_cache
        super().delete(save)


class ImageField(FileField):
    attr_class = ImageFieldFile
    descriptor_class = ImageFileDescriptor
    description = _("Image")

    def __init__(
        self,
        verbose_name=None,
        name=None,
        width_field=None,
        height_field=None,
        **kwargs,
    ):
        self.width_field, self.height_field = width_field, height_field
        super().__init__(verbose_name, name, **kwargs)

    def check(self, **kwargs):
        return [
            *super().check(**kwargs),
            *self._check_image_library_installed(),
        ]

    def _check_image_library_installed(self):
        try:
            from PIL import Image  # NOQA
        except ImportError:
            return [
                checks.Error(
                    "Cannot use ImageField because Pillow is not installed.",
                    hint=(
                        "Get Pillow at https://pypi.org/project/Pillow/ "
                        'or run command "python -m pip install Pillow".'
                    ),
                    obj=self,
                    id="fields.E210",
                )
            ]
        else:
            return []

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.width_field:
            kwargs["width_field"] = self.width_field
        if self.height_field:
            kwargs["height_field"] = self.height_field
        return name, path, args, kwargs

    def contribute_to_class(self, cls, name, **kwargs):
        super().contribute_to_class(cls, name, **kwargs)
        # Attach update_dimension_fields so that dimension fields declared
        # after their corresponding image field don't stay cleared by
        # Model.__init__, see bug #11196.
        # Only run post-initialization dimension update on non-abstract models
        # with width_field/height_field.
        if not cls._meta.abstract and (self.width_field or self.height_field):
            signals.post_init.connect(self.update_dimension_fields, sender=cls)

    def update_dimension_fields(self, instance, force=False, *args, **kwargs):
        """
        Update field's width and height fields, if defined.

        This method is hooked up to model's post_init signal to update
        dimensions after instantiating a model instance.  However, dimensions
        won't be updated if the dimensions fields are already populated.  This
        avoids unnecessary recalculation when loading an object from the
        database.

        Dimensions can be forced to update with force=True, which is how
        ImageFileDescriptor.__set__ calls this method.
        """
        # Nothing to update if the field doesn't have dimension fields or if
        # the field is deferred.
        has_dimension_fields = self.width_field or self.height_field
        if not has_dimension_fields or self.attname not in instance.__dict__:
            return

        # getattr will call the ImageFileDescriptor's __get__ method, which
        # coerces the assigned value into an instance of self.attr_class
        # (ImageFieldFile in this case).
        file = getattr(instance, self.attname)

        # Nothing to update if we have no file and not being forced to update.
        if not file and not force:
            return

        dimension_fields_filled = not (
            (self.width_field and not getattr(instance, self.width_field))
            or (self.height_field and not getattr(instance, self.height_field))
        )
        # When both dimension fields have values, we are most likely loading
        # data from the database or updating an image field that already had
        # an image stored.  In the first case, we don't want to update the
        # dimension fields because we are already getting their values from the
        # database.  In the second case, we do want to update the dimensions
        # fields and will skip this return because force will be True since we
        # were called from ImageFileDescriptor.__set__.
        if dimension_fields_filled and not force:
            return

        # file should be an instance of ImageFieldFile or should be None.
        if file:
            width = file.width
            height = file.height
        else:
            # No file, so clear dimensions fields.
            width = None
            height = None

        # Update the width and height fields.
        if self.width_field:
            setattr(instance, self.width_field, width)
        if self.height_field:
            setattr(instance, self.height_field, height)

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": forms.ImageField,
                **kwargs,
            }
        )
