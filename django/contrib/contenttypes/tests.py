"""
Make sure that the content type cache (see ContentTypeManager) works correctly.
Lookups for a particular content type -- by model or by ID -- should hit the
database only on the first lookup.

First, let's make sure we're dealing with a blank slate (and that DEBUG is on so
that queries get logged)::

    >>> from django.conf import settings
    >>> settings.DEBUG = True

    >>> from django.contrib.contenttypes.models import ContentType
    >>> ContentType.objects.clear_cache()

    >>> from django import db
    >>> db.reset_queries()
    
At this point, a lookup for a ContentType should hit the DB::

    >>> ContentType.objects.get_for_model(ContentType)
    <ContentType: content type>
    
    >>> len(db.connection.queries)
    1

A second hit, though, won't hit the DB, nor will a lookup by ID::

    >>> ct = ContentType.objects.get_for_model(ContentType)
    >>> len(db.connection.queries)
    1
    >>> ContentType.objects.get_for_id(ct.id)
    <ContentType: content type>
    >>> len(db.connection.queries)
    1

Once we clear the cache, another lookup will again hit the DB::

    >>> ContentType.objects.clear_cache()
    >>> ContentType.objects.get_for_model(ContentType)
    <ContentType: content type>
    >>> len(db.connection.queries)
    2

Don't forget to reset DEBUG!

    >>> settings.DEBUG = False
"""