from django.db import connection, models
from django.db.models.functions import Lower


class People(models.Model):
    name = models.CharField(max_length=255)
    parent = models.ForeignKey("self", models.CASCADE)


class Message(models.Model):
    from_field = models.ForeignKey(People, models.CASCADE, db_column="from_id")
    author = models.ForeignKey(People, models.CASCADE, related_name="message_authors")


class PeopleData(models.Model):
    people_pk = models.ForeignKey(People, models.CASCADE, primary_key=True)
    ssn = models.CharField(max_length=11)


class PeopleMoreData(models.Model):
    people_unique = models.ForeignKey(People, models.CASCADE, unique=True)
    message = models.ForeignKey(Message, models.CASCADE, blank=True, null=True)
    license = models.CharField(max_length=255)


class ForeignKeyToField(models.Model):
    to_field_fk = models.ForeignKey(
        PeopleMoreData,
        models.CASCADE,
        to_field="people_unique",
    )


class DigitsInColumnName(models.Model):
    all_digits = models.CharField(max_length=11, db_column="123")
    leading_digit = models.CharField(max_length=11, db_column="4extra")
    leading_digits = models.CharField(max_length=11, db_column="45extra")


class SpecialName(models.Model):
    field = models.IntegerField(db_column="field")
    # Underscores
    field_field_0 = models.IntegerField(db_column="Field_")
    field_field_1 = models.IntegerField(db_column="Field__")
    field_field_2 = models.IntegerField(db_column="__field")
    # Other chars
    prc_x = models.IntegerField(db_column="prc(%) x")
    non_ascii = models.IntegerField(db_column="tamaño")

    class Meta:
        db_table = "inspectdb_special.table name"


class ColumnTypes(models.Model):
    id = models.AutoField(primary_key=True)
    big_int_field = models.BigIntegerField()
    bool_field = models.BooleanField(default=False)
    null_bool_field = models.BooleanField(null=True)
    char_field = models.CharField(max_length=10)
    null_char_field = models.CharField(max_length=10, blank=True, null=True)
    date_field = models.DateField()
    date_time_field = models.DateTimeField()
    decimal_field = models.DecimalField(max_digits=6, decimal_places=1)
    email_field = models.EmailField()
    file_field = models.FileField(upload_to="unused")
    file_path_field = models.FilePathField()
    float_field = models.FloatField()
    int_field = models.IntegerField()
    gen_ip_address_field = models.GenericIPAddressField(protocol="ipv4")
    pos_big_int_field = models.PositiveBigIntegerField()
    pos_int_field = models.PositiveIntegerField()
    pos_small_int_field = models.PositiveSmallIntegerField()
    slug_field = models.SlugField()
    small_int_field = models.SmallIntegerField()
    text_field = models.TextField()
    time_field = models.TimeField()
    url_field = models.URLField()
    uuid_field = models.UUIDField()


class JSONFieldColumnType(models.Model):
    json_field = models.JSONField()
    null_json_field = models.JSONField(blank=True, null=True)

    class Meta:
        required_db_features = {
            "can_introspect_json_field",
            "supports_json_field",
        }


test_collation = connection.features.test_collations.get("non_default")


class CharFieldDbCollation(models.Model):
    char_field = models.CharField(max_length=10, db_collation=test_collation)

    class Meta:
        required_db_features = {"supports_collation_on_charfield"}


class TextFieldDbCollation(models.Model):
    text_field = models.TextField(db_collation=test_collation)

    class Meta:
        required_db_features = {"supports_collation_on_textfield"}


class UniqueTogether(models.Model):
    field1 = models.IntegerField()
    field2 = models.CharField(max_length=10)
    from_field = models.IntegerField(db_column="from")
    non_unique = models.IntegerField(db_column="non__unique_column")
    non_unique_0 = models.IntegerField(db_column="non_unique__column")

    class Meta:
        unique_together = [
            ("field1", "field2"),
            ("from_field", "field1"),
            ("non_unique", "non_unique_0"),
        ]


class FuncUniqueConstraint(models.Model):
    name = models.CharField(max_length=255)
    rank = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("name"), models.F("rank"), name="index_lower_name"
            )
        ]
        required_db_features = {"supports_expression_indexes"}
