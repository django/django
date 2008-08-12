"""
28. Many-to-many relationships between the same two tables

In this example, a ``Person`` can have many friends, who are also ``Person``
objects. Friendship is a symmetrical relationship - if I am your friend, you
are my friend. Here, ``friends`` is an example of a symmetrical
``ManyToManyField``.

A ``Person`` can also have many idols - but while I may idolize you, you may
not think the same of me. Here, ``idols`` is an example of a non-symmetrical
``ManyToManyField``. Only recursive ``ManyToManyField`` fields may be
non-symmetrical, and they are symmetrical by default.

This test validates that the many-to-many table is created using a mangled name
if there is a name clash, and tests that symmetry is preserved where
appropriate.
"""

from django.db import models

class Person(models.Model):
    name = models.CharField(max_length=20)
    friends = models.ManyToManyField('self')
    idols = models.ManyToManyField('self', symmetrical=False, related_name='stalkers')

    def __unicode__(self):
        return self.name

__test__ = {'API_TESTS':"""
>>> a = Person(name='Anne')
>>> a.save()
>>> b = Person(name='Bill')
>>> b.save()
>>> c = Person(name='Chuck')
>>> c.save()
>>> d = Person(name='David')
>>> d.save()

# Add some friends in the direction of field definition
# Anne is friends with Bill and Chuck
>>> a.friends.add(b,c)

# David is friends with Anne and Chuck - add in reverse direction
>>> d.friends.add(a,c)

# Who is friends with Anne?
>>> a.friends.all()
[<Person: Bill>, <Person: Chuck>, <Person: David>]

# Who is friends with Bill?
>>> b.friends.all()
[<Person: Anne>]

# Who is friends with Chuck?
>>> c.friends.all()
[<Person: Anne>, <Person: David>]

# Who is friends with David?
>>> d.friends.all()
[<Person: Anne>, <Person: Chuck>]

# Bill is already friends with Anne - add Anne again, but in the reverse direction
>>> b.friends.add(a)

# Who is friends with Anne?
>>> a.friends.all()
[<Person: Bill>, <Person: Chuck>, <Person: David>]

# Who is friends with Bill?
>>> b.friends.all()
[<Person: Anne>]

# Remove Anne from Bill's friends
>>> b.friends.remove(a)

# Who is friends with Anne?
>>> a.friends.all()
[<Person: Chuck>, <Person: David>]

# Who is friends with Bill?
>>> b.friends.all()
[]

# Clear Anne's group of friends
>>> a.friends.clear()

# Who is friends with Anne?
>>> a.friends.all()
[]

# Reverse relationships should also be gone
# Who is friends with Chuck?
>>> c.friends.all()
[<Person: David>]

# Who is friends with David?
>>> d.friends.all()
[<Person: Chuck>]


# Add some idols in the direction of field definition
# Anne idolizes Bill and Chuck
>>> a.idols.add(b,c)

# Bill idolizes Anne right back
>>> b.idols.add(a)

# David is idolized by Anne and Chuck - add in reverse direction
>>> d.stalkers.add(a,c)

# Who are Anne's idols?
>>> a.idols.all()
[<Person: Bill>, <Person: Chuck>, <Person: David>]

# Who is stalking Anne?
>>> a.stalkers.all()
[<Person: Bill>]

# Who are Bill's idols?
>>> b.idols.all()
[<Person: Anne>]

# Who is stalking Bill?
>>> b.stalkers.all()
[<Person: Anne>]

# Who are Chuck's idols?
>>> c.idols.all()
[<Person: David>]

# Who is stalking Chuck?
>>> c.stalkers.all()
[<Person: Anne>]

# Who are David's idols?
>>> d.idols.all()
[]

# Who is stalking David
>>> d.stalkers.all()
[<Person: Anne>, <Person: Chuck>]

# Bill is already being stalked by Anne - add Anne again, but in the reverse direction
>>> b.stalkers.add(a)

# Who are Anne's idols?
>>> a.idols.all()
[<Person: Bill>, <Person: Chuck>, <Person: David>]

# Who is stalking Anne?
[<Person: Bill>]

# Who are Bill's idols
>>> b.idols.all()
[<Person: Anne>]

# Who is stalking Bill?
>>> b.stalkers.all()
[<Person: Anne>]

# Remove Anne from Bill's list of stalkers
>>> b.stalkers.remove(a)

# Who are Anne's idols?
>>> a.idols.all()
[<Person: Chuck>, <Person: David>]

# Who is stalking Anne?
>>> a.stalkers.all()
[<Person: Bill>]

# Who are Bill's idols?
>>> b.idols.all()
[<Person: Anne>]

# Who is stalking Bill?
>>> b.stalkers.all()
[]

# Clear Anne's group of idols
>>> a.idols.clear()

# Who are Anne's idols
>>> a.idols.all()
[]

# Reverse relationships should also be gone
# Who is stalking Chuck?
>>> c.stalkers.all()
[]

# Who is friends with David?
>>> d.stalkers.all()
[<Person: Chuck>]

"""}
