from ..models import models


class RasterModel(models.Model):
    rast = models.RasterField('A Verbose Raster Name', null=True, srid=4326, spatial_index=True, blank=True)
    rastprojected = models.RasterField('A Projected Raster Table', srid=3086, null=True)
    geom = models.PointField(null=True)

    class Meta:
        required_db_features = ['supports_raster']

    def __str__(self):
        return str(self.id)


class RasterRelatedModel(models.Model):
    rastermodel = models.ForeignKey(RasterModel, models.CASCADE)

    class Meta:
        required_db_features = ['supports_raster']

    def __str__(self):
        return str(self.id)
