from django.contrib.gis.geos import GEOSGeometry, Polygon

def _bbcontains(model, instance_value, value):
    bbox = Polygon.from_bbox(instance_value.extent)
    return bbox.contains(value)

def _bboverlaps(model, instance_value, value):
    bbox = Polygon.from_bbox(instance_value.extent)
    return bbox.overlaps(value)

def _contains(model, instance_value, value):
    return instance_value.contains(value)

def _contained(model, instance_value, value):
    instance_bbox = Polygon.from_bbox(instance_value.extent)
    value_bbox = Polygon.from_bbox(value.extent)
    return value_bbox.conains(instance_bbox)

def _contains_properly(model, instance_value, value):
    return instance_value.relate_pattern(value, 'TFFTFF***')

def _coveredby(model, instance_value, value):
    # T*F**F***, *TF**F***, **FT*F***, **F*TF***
    return any(
            instance_value.relate_pattern(value, 'T*F**F***'),
            instance_value.relate_pattern(value, '*TF**F***'),
            instance_value.relate_pattern(value, '**FT*F***'),
            instance_value.relate_pattern(value, '**F*TF***'),
            )

def _covers(model, instance_value, value):
    # T*****FF*, *T****FF*, ***T**FF*, ****T*FF*
    return any(
            instance_value.relate_pattern(value, 'T*****FF*'),
            instance_value.relate_pattern(value, '*T****FF*'),
            instance_value.relate_pattern(value, '***T**FF*'),
            instance_value.relate_pattern(value, '****T*FF*'),
            )

def _crosses(model, instance_value, value):
    return instance_value.crosses(value)

def _disjoint(model, instance_value, value):
    return instance_value.disjoint(value)

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
    'distance_gt': None,
    'distance_gte': None,
    'distance_lt': None,
    'distance_lte': None,
    'dwithin': None,
    'equals': None,
    'exact': None,
    'intersects': None,
    'overlaps': None,
    'relate': None,
    'same_as': None,
    'touches': None,
    'within': None,
    'left': None,
    'right': None,
    'overlaps_left': None,
    'overlaps_right': None,
    'overlaps_above': None,
    'overlaps_below': None,
    'strictly_above': None,
    'strictly_below': None}


