from django import template

from regressiontests.views import BrokenException

register = template.Library()

def go_boom(arg):
    raise BrokenException(arg)
register.simple_tag(go_boom)
