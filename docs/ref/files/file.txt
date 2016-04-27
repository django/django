===================
The ``File`` object
===================

The :mod:`django.core.files` module and its submodules contain built-in classes
for basic file handling in Django.

.. currentmodule:: django.core.files

The ``File`` class
==================

.. class:: File(file_object)

    The :class:`File` class is a thin wrapper around a Python
    :py:term:`file object` with some Django-specific additions.
    Internally, Django uses this class when it needs to represent a file.

    :class:`File` objects have the following attributes and methods:

    .. attribute:: name

        The name of the file including the relative path from
        :setting:`MEDIA_ROOT`.

    .. attribute:: size

        The size of the file in bytes.

    .. attribute:: file

        The underlying :py:term:`file object` that this class wraps.

        .. admonition:: Be careful with this attribute in subclasses.

            Some subclasses of :class:`File`, including
            :class:`~django.core.files.base.ContentFile` and
            :class:`~django.db.models.fields.files.FieldFile`, may replace this
            attribute with an object other than a Python :py:term:`file object`.
            In these cases, this attribute may itself be a :class:`File`
            subclass (and not necessarily the same subclass). Whenever
            possible, use the attributes and methods of the subclass itself
            rather than the those of the subclass's ``file`` attribute.

    .. attribute:: mode

        The read/write mode for the file.

    .. method:: open(mode=None)

        Open or reopen the file (which also does ``File.seek(0)``).
        The ``mode`` argument allows the same values
        as Python's built-in :func:`python:open()`.

        When reopening a file, ``mode`` will override whatever mode the file
        was originally opened with; ``None`` means to reopen with the original
        mode.

    .. method:: read(num_bytes=None)

        Read content from the file. The optional ``size`` is the number of
        bytes to read; if not specified, the file will be read to the end.

    .. method:: __iter__()

        Iterate over the file yielding one line at a time.

    .. method:: chunks(chunk_size=None)

        Iterate over the file yielding "chunks" of a given size. ``chunk_size``
        defaults to 64 KB.

        This is especially useful with very large files since it allows them to
        be streamed off disk and avoids storing the whole file in memory.

    .. method:: multiple_chunks(chunk_size=None)

        Returns ``True`` if the file is large enough to require multiple chunks
        to access all of its content give some ``chunk_size``.

    .. method:: write(content)

        Writes the specified content string to the file. Depending on the
        storage system behind the scenes, this content might not be fully
        committed until :func:`close()` is called on the file.

    .. method:: close()

        Close the file.

    In addition to the listed methods, :class:`~django.core.files.File` exposes
    the following attributes and methods of its ``file`` object:
    ``encoding``, ``fileno``, ``flush``, ``isatty``, ``newlines``,
    ``read``, ``readinto``, ``readlines``, ``seek``, ``softspace``, ``tell``,
    ``truncate``, ``writelines``, ``xreadlines``. If you are using
    Python 3, the ``seekable`` method is also available.

    .. versionchanged:: 1.9

        The ``seekable`` method was added.

.. currentmodule:: django.core.files.base

The ``ContentFile`` class
=========================

.. class:: ContentFile(File)

    The ``ContentFile`` class inherits from :class:`~django.core.files.File`,
    but unlike :class:`~django.core.files.File` it operates on string content
    (bytes also supported), rather than an actual file. For example::

        from __future__ import unicode_literals
        from django.core.files.base import ContentFile

        f1 = ContentFile("esta sentencia está en español")
        f2 = ContentFile(b"these are bytes")

.. currentmodule:: django.core.files.images

The ``ImageFile`` class
=======================

.. class:: ImageFile(file_object)

    Django provides a built-in class specifically for images.
    :class:`django.core.files.images.ImageFile` inherits all the attributes
    and methods of :class:`~django.core.files.File`, and additionally
    provides the following:

    .. attribute:: width

        Width of the image in pixels.

    .. attribute:: height

        Height of the image in pixels.

.. currentmodule:: django.core.files

Additional methods on files attached to objects
===============================================

Any :class:`File` that is associated with an object (as with ``Car.photo``,
below) will also have a couple of extra methods:

.. method:: File.save(name, content, save=True)

    Saves a new file with the file name and contents provided. This will not
    replace the existing file, but will create a new file and update the object
    to point to it. If ``save`` is ``True``, the model's ``save()`` method will
    be called once the file is saved. That is, these two lines::

        >>> car.photo.save('myphoto.jpg', content, save=False)
        >>> car.save()

    are equivalent to::

        >>> car.photo.save('myphoto.jpg', content, save=True)

    Note that the ``content`` argument must be an instance of either
    :class:`File` or of a subclass of :class:`File`, such as
    :class:`~django.core.files.base.ContentFile`.

.. method:: File.delete(save=True)

    Removes the file from the model instance and deletes the underlying file.
    If ``save`` is ``True``, the model's ``save()`` method will be called once
    the file is deleted.
