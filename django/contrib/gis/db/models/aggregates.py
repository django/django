from django.db.models import Aggregate

__all__ = ['Collect', 'Extent', 'Extent3D', 'MakeLine', 'Union']


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
