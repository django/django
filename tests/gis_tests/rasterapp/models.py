from ..models import models


class RasterModel(models.Model):
    rast = models.RasterField('A Verbose Raster Name', null=True, srid=4326, spatial_index=True, blank=True)

    class Meta:
        required_db_features = ['supports_raster']

    def __str__(self):
        return str(self.id)
