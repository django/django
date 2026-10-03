from django.db.models.constraints import LOOKUP_SEP


def get_field_from_path(model, field_path):
    """
    Recursive helper function to follow a field path across relationships
    and return the final field. For example, given a model Book with a
    ForeignKey to Artist called "artist", and Artist has a DateField called
    "birthday", then _get_field_from_path(Book, "artist__birthday") would
    return the DateField for "birthday" on Artist. Raise a FieldDoesNotExist
    if any step is invalid.
    """

    field_pieces = field_path.split(LOOKUP_SEP)

    for i, piece in enumerate(field_pieces):
        # raises FieldDoesNotExist if the field doesn't exist
        field = model._meta.get_field(piece)

        if field.is_relation:
            return get_field_from_path(
                field.remote_field.model,
                LOOKUP_SEP.join(field_pieces[(i + 1) :]),
            )

        return field
