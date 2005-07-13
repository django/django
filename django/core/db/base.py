from time import time

class CursorDebugWrapper:
    def __init__(self, cursor, db):
        self.cursor = cursor
        self.db = db

    def execute(self, sql, params=[]):
        start = time()
        result = self.cursor.execute(sql, params)
        stop = time()
        self.db.queries.append({
            'sql': sql % tuple(params),
            'time': "%.3f" % (stop - start),
        })
        return result

    def executemany(self, sql, param_list):
        start = time()
        result = self.cursor.executemany(sql, param_list)
        stop = time()
        self.db.queries.append({
            'sql': 'MANY: ' + sql + ' ' + str(tuple(param_list)),
            'time': "%.3f" % (stop - start),
        })
        return result

    def __getattr__(self, attr):
        if self.__dict__.has_key(attr):
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)
