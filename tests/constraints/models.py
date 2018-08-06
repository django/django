from django.db import models


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.IntegerField(null=True)
    discounted_price = models.IntegerField(null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(price__gt=models.F('discounted_price')),
                name='price_gt_discounted_price',
            ),
            models.UniqueConstraint(fields=['name'], name='unique_name'),
        ]
