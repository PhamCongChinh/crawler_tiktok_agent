import logging
import logging.config
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# ======================
# FORMATTER MÀU CHO CONSOLE
# ======================
class ColorFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[41m",  # White on red background
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        msg = super().format(record)
        return f"{color}{msg}{self.RESET}"


# ======================
# CẤU HÌNH FILE LOG
# ======================
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
            "when": "midnight",      # mỗi ngày
            "interval": 1,
            "backupCount": 2,
            "encoding": "utf-8",
        },
    },

    "loggers": {
        "": {
            "handlers": ["file"],
            "level": "INFO"
        }
    }
}

# ======================
# SETUP LOGGING
# ======================
def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        ColorFormatter("%(asctime)s |  %(levelname)s - %(message)s")
    )

    logging.getLogger("").addHandler(console_handler)