import logging
import sys
from logging.handlers import RotatingFileHandler


def new_logger(logger):
    """Настройка логгера пакета."""
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler1 = RotatingFileHandler(
        'work_bot.log', maxBytes=50000000,
        backupCount=5)
    handler1.setFormatter(formatter)
    logger.addHandler(handler1)
    handler2 = logging.StreamHandler(sys.stdout)
    handler2.setFormatter(formatter)
    logger.addHandler(handler2)
    return logger
