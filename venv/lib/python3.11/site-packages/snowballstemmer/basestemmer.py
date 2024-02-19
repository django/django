class BaseStemmer(object):
    def __init__(self):
        self.set_current("")

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

    def go_in_grouping(self, s, min, max):
        while self.cursor < self.limit:
            ch = ord(self.current[self.cursor])
            if ch > max or ch < min:
                return True
            ch -= min
            if (s[ch >> 3] & (0x1 << (ch & 0x7))) == 0:
                return True
            self.cursor += 1
        return False

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

    def go_in_grouping_b(self, s, min, max):
        while self.cursor > self.limit_backward:
            ch = ord(self.current[self.cursor - 1])
            if ch > max or ch < min:
                return True
            ch -= min
            if (s[ch >> 3] & (0x1 << (ch & 0x7))) == 0:
                return True
            self.cursor -= 1
        return False

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

    def go_out_grouping(self, s, min, max):
        while self.cursor < self.limit:
            ch = ord(self.current[self.cursor])
            if ch <= max and ch >= min:
                ch -= min
                if (s[ch >> 3] & (0X1 << (ch & 0x7))):
                    return True
            self.cursor += 1
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

    def go_out_grouping_b(self, s, min, max):
        while self.cursor > self.limit_backward:
            ch = ord(self.current[self.cursor - 1])
            if ch <= max and ch >= min:
                ch -= min
                if (s[ch >> 3] & (0X1 << (ch & 0x7))):
                    return True
            self.cursor -= 1
        return False

    def eq_s(self, s):
        if self.limit - self.cursor < len(s):
            return False
        if self.current[self.cursor:self.cursor + len(s)] != s:
            return False
        self.cursor += len(s)
        return True

    def eq_s_b(self, s):
        if self.cursor - self.limit_backward < len(s):
            return False
        if self.current[self.cursor - len(s):self.cursor] != s:
            return False
        self.cursor -= len(s)
        return True

    def find_among(self, v):
        i = 0
        j = len(v)

        c = self.cursor
        l = self.limit

        common_i = 0
        common_j = 0

        first_key_inspected = False

        while True:
            k = i + ((j - i) >> 1)
            diff = 0
            common = min(common_i, common_j) # smaller
            w = v[k]
            for i2 in range(common, len(w.s)):
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
                # v->s inspected. This looks messy, but is actually
                # the optimal approach.
                if first_key_inspected:
                    break
                first_key_inspected = True
        while True:
            w = v[i]
            if common_i >= len(w.s):
                self.cursor = c + len(w.s)
                if w.method is None:
                    return w.result
                method = getattr(self, w.method)
                res = method()
                self.cursor = c + len(w.s)
                if res:
                    return w.result
            i = w.substring_i
            if i < 0:
                return 0
        return -1 # not reachable

    def find_among_b(self, v):
        '''
        find_among_b is for backwards processing. Same comments apply
        '''
        i = 0
        j = len(v)

        c = self.cursor
        lb = self.limit_backward

        common_i = 0
        common_j = 0

        first_key_inspected = False

        while True:
            k = i + ((j - i) >> 1)
            diff = 0
            common = min(common_i, common_j)
            w = v[k]
            for i2 in range(len(w.s) - 1 - common, -1, -1):
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
            if common_i >= len(w.s):
                self.cursor = c - len(w.s)
                if w.method is None:
                    return w.result
                method = getattr(self, w.method)
                res = method()
                self.cursor = c - len(w.s)
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

    def slice_to(self):
        '''
        Return the slice as a string.
        '''
        result = ''
        if self.slice_check():
            result = self.current[self.bra:self.ket]
        return result

    def assign_to(self):
        '''
        Return the current string up to the limit.
        '''
        return self.current[0:self.limit]

    def stemWord(self, word):
        self.set_current(word)
        self._stem()
        return self.get_current()

    def stemWords(self, words):
        return [self.stemWord(word) for word in words]
