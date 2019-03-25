class BaseStemmer(object):
    def __init__(self):
        self.set_current("")
        self.maxCacheSize = 10000
        self._cache = {}
        self._counter = 0

    def set_current(self, value):
        '''
        Set the self.current string.
        '''
        self.current = value
        self.cursor = 0
        self.limit = len(self.current)
        self.limit_backward = 0
        self.bra = self.cursor
        self.ket = self.limit

    def get_current(self):
        '''
        Get the self.current string.
        '''
        return self.current

    def copy_from(self, other):
        self.current          = other.current
        self.cursor           = other.cursor
        self.limit            = other.limit
        self.limit_backward   = other.limit_backward
        self.bra              = other.bra
        self.ket              = other.ket

    def in_grouping(self, s, min, max):
        if self.cursor >= self.limit:
            return False
        ch = ord(self.current[self.cursor])
        if ch > max or ch < min:
            return False
        ch -= min
        if (s[ch >> 3] & (0x1 << (ch & 0x7))) == 0:
            return False
        self.cursor += 1
        return True

    def in_grouping_b(self, s, min, max):
        if self.cursor <= self.limit_backward:
            return False
        ch = ord(self.current[self.cursor - 1])
        if ch > max or ch < min:
            return False
        ch -= min
        if (s[ch >> 3] & (0x1 << (ch & 0x7))) == 0:
            return False
        self.cursor -= 1
        return True

    def out_grouping(self, s, min, max):
        if self.cursor >= self.limit:
            return False
        ch = ord(self.current[self.cursor])
        if ch > max or ch < min:
            self.cursor += 1
            return True
        ch -= min
        if (s[ch >> 3] & (0X1 << (ch & 0x7))) == 0:
            self.cursor += 1
            return True
        return False

    def out_grouping_b(self, s, min, max):
        if self.cursor <= self.limit_backward:
            return False
        ch = ord(self.current[self.cursor - 1])
        if ch > max or ch < min:
            self.cursor -= 1
            return True
        ch -= min
        if (s[ch >> 3] & (0X1 << (ch & 0x7))) == 0:
            self.cursor -= 1
            return True
        return False

    def in_range(self, min, max):
        if self.cursor >= self.limit:
            return False
        ch = ord(self.current[self.cursor])
        if ch > max or ch < min:
            return False
        self.cursor += 1
        return True

    def in_range_b(self, min, max):
        if self.cursor <= self.limit_backward:
            return False
        ch = ord(self.current[self.cursor - 1])
        if ch > max or ch < min:
            return False
        self.cursor -= 1
        return True

    def out_range(self, min, max):
        if self.cursor >= self.limit:
            return False
        ch = ord(self.current[self.cursor])
        if not (ch > max or ch < min):
            return False
        self.cursor += 1
        return True

    def out_range_b(self, min, max):
        if self.cursor <= self.limit_backward:
            return False
        ch = ord(self.current[self.cursor - 1])
        if not (ch > max or ch < min):
            return False
        self.cursor -= 1
        return True

    def eq_s(self, s_size, s):
        if self.limit - self.cursor < s_size:
            return False
        if self.current[self.cursor:self.cursor + s_size] != s:
            return False
        self.cursor += s_size
        return True

    def eq_s_b(self, s_size, s):
        if self.cursor - self.limit_backward < s_size:
            return False
        if self.current[self.cursor - s_size:self.cursor] != s:
            return False
        self.cursor -= s_size
        return True

    def eq_v(self, s):
        return self.eq_s(len(s), s)

    def eq_v_b(self, s):
        return self.eq_s_b(len(s), s)

    def find_among(self, v, v_size):
        i = 0
        j = v_size

        c = self.cursor
        l = self.limit

        common_i = 0
        common_j = 0

        first_key_inspected = False

        while True:
            k = i + ((j - i) >> 1)
            diff = 0
            common = min(common_i, common_j) # smalle
            w = v[k]
            for i2 in range(common, w.s_size):
                if c + common == l:
                    diff = -1
                    break
                diff = ord(self.current[c + common]) - ord(w.s[i2])
                if diff != 0:
                    break
                common += 1
            if diff < 0:
                j = k
                common_j = common
            else:
                i = k
                common_i = common
            if j - i <= 1:
                if i > 0:
                    break # v->s has been inspected
                if j == i:
                    break # only one item in v
                # - but now we need to go round once more to get
                # v->s inspected. self looks messy, but is actually
                # the optimal approach.
                if first_key_inspected:
                    break
                first_key_inspected = True
        while True:
            w = v[i]
            if common_i >= w.s_size:
                self.cursor = c + w.s_size
                if w.method is None:
                    return w.result
                method = getattr(self, w.method)
                res = method()
                self.cursor = c + w.s_size
                if res:
                    return w.result
            i = w.substring_i
            if i < 0:
                return 0
        return -1 # not reachable

    def find_among_b(self, v, v_size):
        '''
        find_among_b is for backwards processing. Same comments apply
        '''
        i = 0
        j = v_size

        c = self.cursor
        lb = self.limit_backward;

        common_i = 0
        common_j = 0

        first_key_inspected = False

        while True:
            k = i + ((j - i) >> 1)
            diff = 0
            common = min(common_i, common_j)
            w = v[k]
            for i2 in range(w.s_size - 1 - common, -1, -1):
                if c - common == lb:
                    diff = -1
                    break
                diff = ord(self.current[c - 1 - common]) - ord(w.s[i2])
                if diff != 0:
                    break
                common += 1
            if diff < 0:
                j = k
                common_j = common
            else:
                i = k
                common_i = common
            if j - i <= 1:
                if i > 0:
                    break
                if j == i:
                    break
                if first_key_inspected:
                    break
                first_key_inspected = True
        while True:
            w = v[i]
            if common_i >= w.s_size:
                self.cursor = c - w.s_size
                if w.method is None:
                    return w.result
                method = getattr(self, w.method)
                res = method()
                self.cursor = c - w.s_size
                if res:
                    return w.result
            i = w.substring_i
            if i < 0:
                return 0
        return -1 # not reachable

    def replace_s(self, c_bra, c_ket, s):
        '''
        to replace chars between c_bra and c_ket in self.current by the
        chars in s.

        @type c_bra int
        @type c_ket int
        @type s: string
        '''
        adjustment = len(s) - (c_ket - c_bra)
        self.current = self.current[0:c_bra] + s + self.current[c_ket:]
        self.limit += adjustment
        if self.cursor >= c_ket:
            self.cursor += adjustment
        elif self.cursor > c_bra:
            self.cursor = c_bra
        return adjustment

    def slice_check(self):
        if self.bra < 0 or self.bra > self.ket or self.ket > self.limit or self.limit > len(self.current):
            return False
        return True

    def slice_from(self, s):
        '''
        @type s string
        '''
        result = False
        if self.slice_check():
            self.replace_s(self.bra, self.ket, s)
            result = True
        return result

    def slice_del(self):
        return self.slice_from("")

    def insert(self, c_bra, c_ket, s):
        '''
        @type c_bra int
        @type c_ket int
        @type s: string
        '''
        adjustment = self.replace_s(c_bra, c_ket, s)
        if c_bra <= self.bra:
            self.bra += adjustment
        if c_bra <= self.ket:
            self.ket += adjustment

    def slice_to(self, s):
        '''
        Copy the slice into the supplied StringBuffer

        @type s: string
        '''
        result = ''
        if self.slice_check():
            result = self.current[self.bra:self.ket]
        return result

    def assign_to(self, s):
        '''
        @type s: string
        '''
        return self.current[0:self.limit]

    def _stem_word(self, word):
        cache = self._cache.get(word)
        if cache is None:
            self.set_current(word)
            self._stem()
            result = self.get_current()
            self._cache[word] = [result, self._counter]
        else:
            cache[1] = self._counter
            result = cache[0]
        self._counter += 1
        return result

    def _clear_cache(self):
        removecount = int(len(self._cache) - self.maxCacheSize * 8 / 10)
        oldcaches = sorted(self._cache.items(), key=lambda cache: cache[1][1])[0:removecount]
        for key, value in oldcaches:
            del self._cache[key]

    def stemWord(self, word):
        result = self._stem_word(word)
        if len(self._cache) > self.maxCacheSize:
            self._clear_cache()
        return result

    def stemWords(self, words):
        result = [self._stem_word(word) for word in words]
        if len(self._cache) > self.maxCacheSize:
            self._clear_cache()
        return result
