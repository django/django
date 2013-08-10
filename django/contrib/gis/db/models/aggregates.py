from django.db.models import Aggregate

class Collect(Aggregate):
    name = 'Collect'

class Extent(Aggregate):
    name = 'Extent'

class Extent3D(Aggregate):
    name = 'Extent3D'

class MakeLine(Aggregate):
    name = 'MakeLine'

class Union(Aggregate):
    name = 'Union'
