from order_with_respect_to.tests import (
    OrderWithRespectToTests, OrderWithRespectToTests2,
)

from .models import Answer, Post, Question


class OrderWithRespectToGFKTests(OrderWithRespectToTests):
    Answer = Answer
    Question = Question

del OrderWithRespectToTests


class OrderWithRespectToGFKTests2(OrderWithRespectToTests2):
    Post = Post

del OrderWithRespectToTests2
