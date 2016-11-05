from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.IntegerField()
    discounted_price = models.IntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                models.Q(price__gt=models.F('discounted_price')),
                'price_gt_discounted_price'
            )
        ]
