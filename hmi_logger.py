import logging
import os
import sys
import tempfile
from pathlib import Path
from logging.handlers import RotatingFileHandler

logger = logging.getLogger(__name__)


# private global
_LOG_FILE: Path | None = None


def get_log_path(app_name: str, use_temp=False):
    """
    Return a safe, per-user log file path.
    If use_temp=True, logs will go into the system temp folder.
    """

    if use_temp:
        base = Path(tempfile.gettempdir())
    else:
        if sys.platform.startswith("win"):
            base = Path(os.getenv("LOCALAPPDATA", Path.home()))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:  # Linux and others
            base = Path.home() / ".local" / "share"

    log_dir = base / app_name / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{app_name}.log"


def setup_logging(
    appName: str,
    level=logging.INFO,
    max_bytes: int = 2 * 1024 * 1024,
    backup_count: int = 5,
):
    """
    Set up rotating file logging for the given app.
    - max_bytes: max size per log file (default 2 MB)
    - backup_count: number of rotated log files to keep (default 5)
    """
    global _LOG_FILE
    logfile = get_log_path(appName)
    _LOG_FILE = logfile

    handler = RotatingFileHandler(logfile, maxBytes=max_bytes, backupCount=backup_count)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %I:%M:%S %p",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()  # clear old handlers if re-called
    root_logger.addHandler(handler)


def get_log_file() -> Path | None:
    """
    Public read-only accessor for the log file path.
    Returns None if setup_logging() hasn't been called yet.
    """
    return _LOG_FILE
