# coding: utf-8

r"""
>>> from django.contrib.comments.models import Comment
>>> from django.contrib.auth.models import User
>>> u = User.objects.create_user('commenttestuser', 'commenttest@example.com', 'testpw')
>>> c = Comment(user=u, comment=u'\xe2')
>>> c
<Comment: commenttestuser: â...>
>>> print c
commenttestuser: â...
"""

