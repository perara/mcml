import logging
logging.basicConfig(level=logging.WARNING)

LEVEL = logging.DEBUG


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(LEVEL)
    return logger