from django.db.models import Aggregate

class Extent(Aggregate):
    name = 'Extent'

class MakeLine(Aggregate):
    name = 'MakeLine'

class Union(Aggregate):
    name = 'Union'
