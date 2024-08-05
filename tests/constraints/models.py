from django.db import models


class Product(models.Model):
    price = models.IntegerField(null=True)
    discounted_price = models.IntegerField(null=True)
    unit = models.CharField(max_length=15, null=True)

    class Meta:
        required_db_features = {
            "supports_table_check_constraints",
        }
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price__gt=models.F("discounted_price")),
                name="price_gt_discounted_price",
            ),
            models.CheckConstraint(
                condition=models.Q(price__gt=0),
                name="%(app_label)s_%(class)s_price_gt_0",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(unit__isnull=True) | models.Q(unit__in=["μg/mL", "ng/mL"])
                ),
                name="unicode_unit_list",
            ),
        ]


class UniqueConstraintProduct(models.Model):
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=32, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "color"],
                name="name_color_uniq",
                # Custom message and error code are ignored.
                violation_error_code="custom_code",
                violation_error_message="Custom message",
            )
        ]


class ChildUniqueConstraintProduct(UniqueConstraintProduct):
    pass


class UniqueConstraintConditionProduct(models.Model):
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=32, null=True)

    class Meta:
        required_db_features = {"supports_partial_indexes"}
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="name_without_color_uniq",
                condition=models.Q(color__isnull=True),
            ),
        ]


class UniqueConstraintDeferrable(models.Model):
    name = models.CharField(max_length=255)
    shelf = models.CharField(max_length=31)

    class Meta:
        required_db_features = {
            "supports_deferrable_unique_constraints",
        }
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="name_init_deferred_uniq",
                deferrable=models.Deferrable.DEFERRED,
            ),
            models.UniqueConstraint(
                fields=["shelf"],
                name="sheld_init_immediate_uniq",
                deferrable=models.Deferrable.IMMEDIATE,
            ),
        ]


class UniqueConstraintInclude(models.Model):
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=32, null=True)

    class Meta:
        required_db_features = {
            "supports_table_check_constraints",
            "supports_covering_indexes",
        }
        constraints = [
            models.UniqueConstraint(
                fields=["name"],
                name="name_include_color_uniq",
                include=["color"],
            ),
        ]


class AbstractModel(models.Model):
    age = models.IntegerField()

    class Meta:
        abstract = True
        required_db_features = {
            "supports_table_check_constraints",
        }
        constraints = [
            models.CheckConstraint(
                condition=models.Q(age__gte=18),
                name="%(app_label)s_%(class)s_adult",
            ),
        ]


class ChildModel(AbstractModel):
    pass


class JSONFieldModel(models.Model):
    data = models.JSONField(null=True)

    class Meta:
        required_db_features = {"supports_json_field"}


class ModelWithDatabaseDefault(models.Model):
    field = models.CharField(max_length=255)
    field_with_db_default = models.CharField(
        max_length=255, db_default=models.Value("field_with_db_default")
    )
