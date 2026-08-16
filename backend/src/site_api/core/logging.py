import sys

from loguru import logger


def configure_logging(level: str) -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level=level.upper(),
        serialize=False,
        backtrace=False,
        diagnose=False,
    )
