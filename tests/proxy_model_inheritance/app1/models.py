from app2.models import NiceModel


class ProxyModel(NiceModel):
    class Meta:
        proxy = True
