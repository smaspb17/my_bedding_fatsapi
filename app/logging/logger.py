# logging/logger.py
import logging
import os

# from rich.logging import RichHandler
import colorlog
from app.core.config import settings


class CustomColoredFormatter(colorlog.ColoredFormatter):
    def format(self, record):
        # Относительный путь с номером строки
        rel_path = os.path.relpath(record.pathname)
        record.custom_path = f"{rel_path}:{record.lineno}"

        # levelname с двоеточием и выравниванием до 9 символов (например "WARNING: ")
        record.levelname_colon = f"{record.levelname + ':':<9}"
        return super().format(record)


def configure_logging(
    level: int = getattr(logging, settings.LOG_LEVEL.upper())
):
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        CustomColoredFormatter(
            fmt=(
                "%(log_color)s%(levelname_colon)-10s"
                "%(blue)s%(asctime)s - "
                "%(white)s%(module)-10s %(message)-10s "
                "%(blue)s(%(custom_path)s)%(reset)s"
            ),
            datefmt="%Y-%m-%d %H:%M:%S",
            reset=True,
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red,bg_white",
            },
            secondary_log_colors={
                "asctime": {
                    "DEBUG": "blue",
                    "INFO": "blue",
                    "WARNING": "blue",
                    "ERROR": "blue",
                    "CRITICAL": "blue",
                },
            },
            style="%",
        )
    )

    logging.basicConfig(
        level=level,
        # datefmt="%Y-%m-%d %H:%M:%S",
        # format=("%(levelname)-8s %(asctime)s %(module)-15s %(message)s"),
        handlers=[handler],
    )
    # logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    # logging.getLogger("fastapi.api").setLevel(logging.ERROR)
