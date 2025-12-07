try:
    import coverage
except ImportError:
    pass
else:
    coverage.process_startup()
