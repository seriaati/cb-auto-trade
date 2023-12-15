import contextlib
import logging
import logging.handlers

__all__ = ("setup_logging",)


@contextlib.contextmanager
def setup_logging():
    log = logging.getLogger()

    try:
        # __enter__
        log.setLevel(logging.INFO)
        logging.getLogger("shioaji").setLevel(logging.CRITICAL)
        handler = logging.StreamHandler()
        file_handler = logging.handlers.RotatingFileHandler(
            "cbat.log", maxBytes=1024 * 1024, backupCount=5
        )
        dt_fmt = "%Y-%m-%d %H:%M:%S"
        fmt = logging.Formatter(
            "[{asctime}] [{levelname}] {name}: {message}", dt_fmt, style="{"
        )
        handler.setFormatter(fmt)
        file_handler.setFormatter(fmt)
        log.addHandler(handler)
        log.addHandler(file_handler)

        yield
    finally:
        # __exit__
        handlers = log.handlers[:]
        for handler in handlers:
            handler.close()
            log.removeHandler(handler)
