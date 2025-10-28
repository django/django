from django.db import models


class ConstraintField(models.CharField):
    """A field that contributes a DB contraint to the model's Meta"""

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only)
        cls._meta.constraints.append(
            models.CheckConstraint(
                check=models.Q(**{name: "valid"}),
                name=f"test_constraint_{cls.__name__.lower()}",
            )
        )


class ChoiceField(models.CharField):
    """A field that contributes a DB contraint to the model's Meta
    to enforce choice values"""

    def contribute_to_class(self, cls, name, private_only=False):
        super().contribute_to_class(cls, name, private_only)
        accepted_values = [c[0] for c in self.choices]
        cls._meta.constraints.append(
            models.CheckConstraint(
                check=models.Q(**{f"{name}__in": accepted_values}),
                name=f"%(app_label)s_%(class)s_{name}_valid_choices",
            )
        )
