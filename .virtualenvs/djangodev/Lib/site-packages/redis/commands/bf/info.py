from ..helpers import nativestr


class BFInfo(object):
    capacity = None
    size = None
    filterNum = None
    insertedNum = None
    expansionRate = None

    def __init__(self, args):
        response = dict(zip(map(nativestr, args[::2]), args[1::2]))
        self.capacity = response["Capacity"]
        self.size = response["Size"]
        self.filterNum = response["Number of filters"]
        self.insertedNum = response["Number of items inserted"]
        self.expansionRate = response["Expansion rate"]

    def get(self, item):
        try:
            return self.__getitem__(item)
        except AttributeError:
            return None

    def __getitem__(self, item):
        return getattr(self, item)


class CFInfo(object):
    size = None
    bucketNum = None
    filterNum = None
    insertedNum = None
    deletedNum = None
    bucketSize = None
    expansionRate = None
    maxIteration = None

    def __init__(self, args):
        response = dict(zip(map(nativestr, args[::2]), args[1::2]))
        self.size = response["Size"]
        self.bucketNum = response["Number of buckets"]
        self.filterNum = response["Number of filters"]
        self.insertedNum = response["Number of items inserted"]
        self.deletedNum = response["Number of items deleted"]
        self.bucketSize = response["Bucket size"]
        self.expansionRate = response["Expansion rate"]
        self.maxIteration = response["Max iterations"]

    def get(self, item):
        try:
            return self.__getitem__(item)
        except AttributeError:
            return None

    def __getitem__(self, item):
        return getattr(self, item)


class CMSInfo(object):
    width = None
    depth = None
    count = None

    def __init__(self, args):
        response = dict(zip(map(nativestr, args[::2]), args[1::2]))
        self.width = response["width"]
        self.depth = response["depth"]
        self.count = response["count"]

    def __getitem__(self, item):
        return getattr(self, item)


class TopKInfo(object):
    k = None
    width = None
    depth = None
    decay = None

    def __init__(self, args):
        response = dict(zip(map(nativestr, args[::2]), args[1::2]))
        self.k = response["k"]
        self.width = response["width"]
        self.depth = response["depth"]
        self.decay = response["decay"]

    def __getitem__(self, item):
        return getattr(self, item)


class TDigestInfo(object):
    compression = None
    capacity = None
    merged_nodes = None
    unmerged_nodes = None
    merged_weight = None
    unmerged_weight = None
    total_compressions = None
    memory_usage = None

    def __init__(self, args):
        response = dict(zip(map(nativestr, args[::2]), args[1::2]))
        self.compression = response["Compression"]
        self.capacity = response["Capacity"]
        self.merged_nodes = response["Merged nodes"]
        self.unmerged_nodes = response["Unmerged nodes"]
        self.merged_weight = response["Merged weight"]
        self.unmerged_weight = response["Unmerged weight"]
        self.total_compressions = response["Total compressions"]
        self.memory_usage = response["Memory usage"]

    def get(self, item):
        try:
            return self.__getitem__(item)
        except AttributeError:
            return None

    def __getitem__(self, item):
        return getattr(self, item)
