import logging

handler = logging.StreamHandler()


def setup_logger(name, verbosity=1):
    """
    Basic logger for runserver etc.
    """

    formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    handler.setFormatter(formatter)

    # Set up main logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    if verbosity > 1:
        logger.setLevel(logging.DEBUG)

    # Set up daphne protocol loggers
    for module in ["daphne.ws_protocol", "daphne.http_protocol", "daphne.server"]:
        daphne_logger = logging.getLogger(module)
        daphne_logger.addHandler(handler)
        daphne_logger.setLevel(
            logging.DEBUG if verbosity > 1 else logging.INFO)

    logger.propagate = False
    return logger
