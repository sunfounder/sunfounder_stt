"""Logging utilities — ANSI-coloured console formatter and rotating-file logger."""

import logging
from logging.handlers import RotatingFileHandler

DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

class ColoredFormatter(logging.Formatter):
    """ANSI-coloured log formatter.

    Wraps the level name in terminal colour escape sequences:
    DEBUG=Blue, INFO=Green, WARNING=Yellow, ERROR=Red, CRITICAL=Purple.
    """

    COLOR_CODES = {
        'DEBUG': '\033[94m',    # Blue
        'INFO': '\033[92m',     # Green
        'WARNING': '\033[93m',  # Yellow
        'ERROR': '\033[91m',    # Red
        'CRITICAL': '\033[95m'  # Purple
    }
    RESET_CODE = '\033[0m'     # Reset

    def format(self, record):
        """Format a log record with ANSI colour codes.

        Args:
            record: :class:`logging.LogRecord` to format.

        Returns:
            str: Formatted log message with colour-annotated level name.
        """
        levelname = record.levelname
        color_code = self.COLOR_CODES.get(levelname, '')
        reset_code = self.RESET_CODE if color_code else ''
        # Apply color code while keeping original format
        record.levelname = f'{color_code}{levelname}{reset_code}'
        return super().format(record)

class Logger(logging.Logger):
    """Logger with console (coloured) and optional rotating-file output.

    Args:
        name: Logger name, default ``"logger"``.
        level: Log level, default :data:`logging.INFO`.
        file: Log file path. ``None`` disables file logging (default).
        maxBytes: Max log file size in bytes before rotation (default 10 MB).
        backupCount: Number of backup files to keep (default 10).
    """
    def __init__(self, name='logger', level=logging.INFO, file:str=None, maxBytes=10*1024*1024, backupCount=10):
        self.log_path = file
        super().__init__(name, level=level)

        # Create a handler, used for output to the console
        console_formatter = ColoredFormatter('[%(levelname)s] %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(console_formatter)
        self.addHandler(console_handler)

        if file is not None:
            # Create a handler, used for output to a file
            file_formatter = logging.Formatter('%(asctime)s.%(msecs)03d [%(levelname)s] %(message)s', datefmt='%y/%m/%d %H:%M:%S')
            file_handler = RotatingFileHandler(self.log_path, maxBytes=maxBytes, backupCount=backupCount)
            file_handler.setLevel(level)
            file_handler.setFormatter(file_formatter)
            self.addHandler(file_handler)

    def setLevel(self, level: [int, str]):
        """Set log level on the logger and all its handlers.

        Args:
            level: Log level as int (e.g. ``logging.DEBUG``) or str
                   (e.g. ``"DEBUG"``) — case-insensitive.

        Returns:
            None
        """
        if isinstance(level, str):
            level = level.upper()
        super().setLevel(level)
        for handler in self.handlers:
            handler.setLevel(level)
