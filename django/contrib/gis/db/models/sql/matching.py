from django.contrib.gis.geos import Polygon


def _bbcontains(model, instance_value, value):
    bbox = Polygon.from_bbox(instance_value.extent)
    return bbox.contains(value)


def _bboverlaps(model, instance_value, value):
    instance_bbox = Polygon.from_bbox(instance_value.extent)
    value_bbox = Polygon.from_bbox(value.extent)
    return instance_bbox.overlaps(value_bbox)


def _contains(model, instance_value, value):
    return instance_value.contains(value)


def _contained(model, instance_value, value):
    instance_bbox = Polygon.from_bbox(instance_value.extent)
    value_bbox = Polygon.from_bbox(value.extent)
    return value_bbox.contains(instance_bbox)


def _contains_properly(model, instance_value, value):
    return instance_value.relate_pattern(value, 'T**FF*FF*')


def _coveredby(model, instance_value, value):
    return any((
            instance_value.relate_pattern(value, 'T*F**F***'),
            instance_value.relate_pattern(value, '*TF**F***'),
            instance_value.relate_pattern(value, '**FT*F***'),
            instance_value.relate_pattern(value, '**F*TF***'),
            ))


def _covers(model, instance_value, value):
    return any((
            instance_value.relate_pattern(value, 'T*****FF*'),
            instance_value.relate_pattern(value, '*T****FF*'),
            instance_value.relate_pattern(value, '***T**FF*'),
            instance_value.relate_pattern(value, '****T*FF*'),
            ))


def _crosses(model, instance_value, value):
    return instance_value.crosses(value)


def _disjoint(model, instance_value, value):
    return instance_value.disjoint(value)


def _equals(model, instance_value, value):
    return instance_value.equals(value)


def _exact(model, instance_value, value):
    return instance_value.equals_exact(value)


def _intersects(model, instance_value, value):
    return instance_value.intersects(value)


def _overlaps(model, instance_value, value):
    return instance_value.overlaps(value)


def _relate(model, instance_value, value):
    other, pattern = value
    return instance_value.relate_pattern(other, pattern)


def _touches(model, instance_value, value):
    return instance_value.touches(value)


def _within(model, instance_value, value):
    return instance_value.within(value)


def _left(model, instance_value, value):
    ixmin, iymin, ixmax, iymax = instance_value.extent
    vxmin, vymin, vxmax, vymax = value.extent
    return ixmax < vxmin


def _right(model, instance_value, value):
    ixmin, iymin, ixmax, iymax = instance_value.extent
    vxmin, vymin, vxmax, vymax = value.extent
    return ixmin > vxmax


def _above(model, instance_value, value):
    ixmin, iymin, ixmax, iymax = instance_value.extent
    vxmin, vymin, vxmax, vymax = value.extent
    return iymin > vymax


def _below(model, instance_value, value):
    ixmin, iymin, ixmax, iymax = instance_value.extent
    vxmin, vymin, vxmax, vymax = value.extent
    return iymax < vymin


def _overlaps_left(model, instance_value, value):
    return (_overlaps(model, instance_value, value) or
            _left(model, instance_value, value))


def _overlaps_right(model, instance_value, value):
    return (_overlaps(model, instance_value, value) or
            _right(model, instance_value, value))


def _overlaps_above(model, instance_value, value):
    return (_overlaps(model, instance_value, value) or
            _above(model, instance_value, value))


def _overlaps_below(model, instance_value, value):
    return (_overlaps(model, instance_value, value) or
            _below(model, instance_value, value))


def _distance_gt(model, instance_value, value):
    other, measure = value
    return instance_value.distance(other) > measure.standard


def _distance_gte(model, instance_value, value):
    other, measure = value
    return instance_value.distance(other) >= measure.standard


def _distance_lt(model, instance_value, value):
    other, measure = value
    return instance_value.distance(other) < measure.standard


def _distance_lte(model, instance_value, value):
    other, measure = value
    return instance_value.distance(other) <= measure.standard


def _dwithin(model, instance_value, value):
    # TODO - unclear if there is any difference between lte and within
    return _distance_lte(model, instance_value, value)


match_functions = {
    'bbcontains': _bbcontains,
    'bboverlaps': _bboverlaps,
    'contained': _contained,
    'contains': _contains,
    'contains_properly': _contains_properly,
    'coveredby': _coveredby,
    'covers': _covers,
    'crosses': _crosses,
    'disjoint': _disjoint,
    'distance_gt': _distance_gt,
    'distance_gte': _distance_gte,
    'distance_lt': _distance_lt,
    'distance_lte': _distance_lte,
    'dwithin': None,
    'equals': _equals,
    'exact': _exact,
    'intersects': _intersects,
    'overlaps': _overlaps,
    'relate': _relate,
    'same_as': _exact,
    'touches': _touches,
    'within': _within,
    'left': _left,
    'right': _right,
    'overlaps_left': _overlaps_left,
    'overlaps_right': _overlaps_right,
    'overlaps_above': _overlaps_above,
    'overlaps_below': _overlaps_below,
    'strictly_above': _above,
    'strictly_below': _below}
