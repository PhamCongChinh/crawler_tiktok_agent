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
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },

    "handlers": {
        # File handler viết ra file, không màu
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "filename": "logs/app.log",
            "encoding": "utf-8",
        },
    },

    "loggers": {
        "": {
            "handlers": ["file"],
            "level": "DEBUG",
            "propagate": True
        }
    }
}

# ======================
# SETUP LOGGING
# ======================
def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)

    # Console handler màu
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        ColorFormatter("%(asctime)s | %(name)s | %(levelname)s - %(message)s")
    )

    # Gắn vào root logger
    logging.getLogger("").addHandler(console_handler)