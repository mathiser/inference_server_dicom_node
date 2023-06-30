import logging


def log(func):
    def wrapper(*args, **kwargs):
        logging.debug(f"[ ] Running func: {func}")
        ret = func(*args, **kwargs)
        logging.debug(f"[X] Running func: {func}")
        return ret
    return wrapper