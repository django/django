=========================
Related objects reference
=========================

.. currentmodule:: django.db.models.fields.related

.. class:: RelatedManager

    A "related manager" is a manager used in a one-to-many or many-to-many
    related context. This happens in two cases:

    * The "other side" of a :class:`~django.db.models.ForeignKey` relation.
      That is::

            class Reporter(models.Model):
                ...

            class Article(models.Model):
                reporter = models.ForeignKey(Reporter)

      In the above example, the methods below will be available on
      the manager ``reporter.article_set``.

    * Both sides of a :class:`~django.db.models.ManyToManyField` relation::

            class Topping(models.Model):
                ...

            class Pizza(models.Model):
                toppings = models.ManyToManyField(Topping)

      In this example, the methods below will be available both on
      ``topping.pizza_set`` and on ``pizza.toppings``.

    These related managers have some extra methods:

    .. method:: add(obj1, [obj2, ...])

        Adds the specified model objects to the related object set.

        Example::

            >>> b = Blog.objects.get(id=1)
            >>> e = Entry.objects.get(id=234)
            >>> b.entry_set.add(e) # Associates Entry e with Blog b.

    .. method:: create(**kwargs)

        Creates a new object, saves it and puts it in the related object set.
        Returns the newly created object::

            >>> b = Blog.objects.get(id=1)
            >>> e = b.entry_set.create(
            ...     headline='Hello',
            ...     body_text='Hi',
            ...     pub_date=datetime.date(2005, 1, 1)
            ... )

            # No need to call e.save() at this point -- it's already been saved.

        This is equivalent to (but much simpler than)::

            >>> b = Blog.objects.get(id=1)
            >>> e = Entry(
            ...     blog=b,
            ...     headline='Hello',
            ...     body_text='Hi',
            ...     pub_date=datetime.date(2005, 1, 1)
            ... )
            >>> e.save(force_insert=True)

        Note that there's no need to specify the keyword argument of the model
        that defines the relationship. In the above example, we don't pass the
        parameter ``blog`` to ``create()``. Django figures out that the new
        ``Entry`` object's ``blog`` field should be set to ``b``.

    .. method:: remove(obj1, [obj2, ...])

        Removes the specified model objects from the related object set::

            >>> b = Blog.objects.get(id=1)
            >>> e = Entry.objects.get(id=234)
            >>> b.entry_set.remove(e) # Disassociates Entry e from Blog b.

        In order to prevent database inconsistency, this method only exists on
        :class:`~django.db.models.ForeignKey` objects where ``null=True``. If
        the related field can't be set to ``None`` (``NULL``), then an object
        can't be removed from a relation without being added to another. In the
        above example, removing ``e`` from ``b.entry_set()`` is equivalent to
        doing ``e.blog = None``, and because the ``blog``
        :class:`~django.db.models.ForeignKey` doesn't have ``null=True``, this
        is invalid.

    .. method:: clear()

        Removes all objects from the related object set::

            >>> b = Blog.objects.get(id=1)
            >>> b.entry_set.clear()

        Note this doesn't delete the related objects -- it just disassociates
        them.

        Just like ``remove()``, ``clear()`` is only available on
        :class:`~django.db.models.ForeignKey`\s where ``null=True``.
