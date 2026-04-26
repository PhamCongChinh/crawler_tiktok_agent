import logging
import logging.config
from pathlib import Path

LOG_DIR = Path("logs")


class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG":    "\033[36m",
        "INFO":     "\033[32m",
        "WARNING":  "\033[33m",
        "ERROR":    "\033[31m",
        "CRITICAL": "\033[41m",
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        return f"{color}{super().format(record)}{self.RESET}"


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": "logs/app.log",
            "when": "midnight",
            "interval": 1,
            "backupCount": 2,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "": {
            "handlers": ["file"],
            "level": "INFO",
        }
    },
}


def setup_logging() -> None:
    # Tránh add handler trùng nếu gọi nhiều lần
    root = logging.getLogger("")
    if root.handlers:
        return

    LOG_DIR.mkdir(exist_ok=True)
    logging.config.dictConfig(LOGGING_CONFIG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        ColorFormatter("%(asctime)s |  %(levelname)s - %(message)s")
    )
    root.addHandler(console_handler)
