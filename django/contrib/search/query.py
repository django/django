class QueryParser(object):
    # TODO: Make a common query language for all the backends.
    pass


class ResultSet(object):
    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def __getitem__(self):
        raise NotImplementedError


class Hit(object):
    def __init__(self, data, indexer):
        self.indexer = indexer
        self.model = indexer.model
        self.data = data

    def get_instance(self):
        name = self.model._meta.pk.name
        pk = self.model._meta.pk.to_python(self.get_pk())
        return self.model.objects.get(**{name: pk})

    instance = property(get_instance)

    def get_pk(self):
        raise NotImplementedError

    def __repr__(self):
        return "<%s: %s %s, Score: %s>" % (self.__class__.__name__,
                                           self.model._meta,
                                           self.get_pk(), self.score)