from django.apps import AppConfig


class ModelDefaultPKConfig(AppConfig):
    name = "model_options"


class ModelPKConfig(AppConfig):
    name = "model_options"
    default_auto_field = "django.db.models.SmallAutoField"


class ModelNewPKConfig(AppConfig):
    name = "model_options"
    default_pk_field = "model_options.test_default_pk.UUID4DefaultPrimaryKeyField"


class ModelBothPKConfig(ModelPKConfig):
    default_pk_field = "model_options.test_default_pk.UUID4DefaultPrimaryKeyField"


class ModelPKNonFieldConfig(AppConfig):
    name = "model_options"
    default_pk_field = "django.db.models.Model"


class ModelPKNonexistentFieldConfig(AppConfig):
    name = "model_options"
    default_pk_field = "django.db.models.NonexistentField"


class ModelPKEmptyFieldConfig(AppConfig):
    name = "model_options"
    default_pk_field = None


class ModelPKNonAutoConfig(AppConfig):
    name = "model_options"
    default_auto_field = "django.db.models.TextField"


class ModelPKNoneConfig(AppConfig):
    name = "model_options"
    default_auto_field = None


class ModelPKNonexistentConfig(AppConfig):
    name = "model_options"
    default_auto_field = "django.db.models.NonexistentAutoField"
