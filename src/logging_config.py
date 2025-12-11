import logging
import logging.config
from pathlib import Path

# Tạo folder logs nếu chưa có
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,

    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "simple": {
            "format": "%(levelname)s - %(message)s"
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "standard",
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": "logs/app.log",
            "encoding": "utf-8",
        },
    },

    "loggers": {
        "": {  # root logger
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": True
        }
    }
}


def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)