"""
26. Many-to-many relationships between the same two tables

In this example, A Person can have many friends, who are also people. Friendship is a 
symmetrical relationshiup - if I am your friend, you are my friend.

This test validates that the m2m table will create a mangled name for the m2m table if
there will be a clash, and tests that symmetry is preserved where appropriate. 
"""

from django.db import models

class Person(models.Model):
    name = models.CharField(maxlength=20)
    friends = models.ManyToManyField('self')

    def __repr__(self):
        return self.name

API_TESTS = """
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
[Bill, Chuck, David]

# Who is friends with Bill?
>>> b.friends.all()
[Anne]

# Who is friends with Chuck?
>>> c.friends.all()
[Anne, David]

# Who is friends with David?
>>> d.friends.all() 
[Anne, Chuck]

# Bill is already friends with Anne - add Anne again, but in the reverse direction
>>> b.friends.add(a)

# Who is friends with Anne?
>>> a.friends.all() 
[Bill, Chuck, David]

# Who is friends with Bill?
>>> b.friends.all()
[Anne]

# Remove Anne from Bill's friends
>>> b.friends.remove(a)

# Who is friends with Anne?
>>> a.friends.all() 
[Chuck, David]

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
[David]

# Who is friends with David?
>>> d.friends.all() 
[Chuck]


"""
