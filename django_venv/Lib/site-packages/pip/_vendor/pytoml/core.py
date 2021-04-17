class TomlError(RuntimeError):
    def __init__(self, message, line, col, filename):
        RuntimeError.__init__(self, message, line, col, filename)
        self.message = message
        self.line = line
        self.col = col
        self.filename = filename

    def __str__(self):
        return '{}({}, {}): {}'.format(self.filename, self.line, self.col, self.message)

    def __repr__(self):
        return 'TomlError({!r}, {!r}, {!r}, {!r})'.format(self.message, self.line, self.col, self.filename)
