"""
Centralized logging configuration for the backend application.
Integrates with Gunicorn's logging system.
"""
import logging
import sys
import os
from logging.handlers import RotatingFileHandler
import traceback
from functools import wraps
import time


class RequestIdFilter(logging.Filter):
    """Add request ID to log records if available."""

    def filter(self, record):
        from flask import g, has_request_context

        if has_request_context():
            record.request_id = getattr(g, 'request_id', '-')
            record.user_id = getattr(g, 'user_id', '-')
            record.device_id = getattr(g, 'device_id', '-')
        else:
            record.request_id = '-'
            record.user_id = '-'
            record.device_id = '-'

        return True


class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors for console output."""

    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        if sys.stderr.isatty():  # Only colorize if outputting to terminal
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return super().format(record)


def setup_logging(app=None):
    """
    Setup logging configuration.

    When running under Gunicorn:
    - Logs go to stdout/stderr (captured by Gunicorn)
    - Gunicorn's error logger is used as the parent
    - Logs appear in /var/log/gunicorn/plushie-ai-error.log

    Args:
        app: Flask application instance (optional)
    """
    # Get log level from environment, default to INFO
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_level = getattr(logging, log_level, logging.INFO)

    # Create logs directory if it doesn't exist
    log_dir = '/home/ec2-user/backend/logs'
    os.makedirs(log_dir, exist_ok=True)

    # Define log format with request context
    log_format = (
        '[%(asctime)s] [%(levelname)s] '
        '[%(name)s:%(funcName)s:%(lineno)d] '
        '[ReqID:%(request_id)s] [User:%(user_id)s] [Device:%(device_id)s] '
        '%(message)s'
    )

    # Simple format for console (less verbose)
    console_format = (
        '[%(asctime)s] [%(levelname)s] [%(name)s] '
        '[ReqID:%(request_id)s] %(message)s'
    )

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove any existing handlers
    root_logger.handlers.clear()

    # Check if running under Gunicorn
    if app and app.logger.handlers:
        # Running under Gunicorn - use Gunicorn's error handler
        gunicorn_error_logger = logging.getLogger('gunicorn.error')
        app.logger.handlers = gunicorn_error_logger.handlers
        app.logger.setLevel(gunicorn_error_logger.level)

        # Add request ID filter to Gunicorn handlers
        for handler in gunicorn_error_logger.handlers:
            handler.addFilter(RequestIdFilter())
            # Update formatter to include our custom fields
            handler.setFormatter(logging.Formatter(log_format))

        # Set root logger to use same handlers
        root_logger.handlers = gunicorn_error_logger.handlers
        root_logger.setLevel(gunicorn_error_logger.level)

        app.logger.info("Logging configured for Gunicorn deployment")
    else:
        # Development mode - log to console and file

        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_formatter = ColoredFormatter(console_format)
        console_handler.setFormatter(console_formatter)
        console_handler.addFilter(RequestIdFilter())

        # File handler (rotating)
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'app.log'),
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(log_format)
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(RequestIdFilter())

        # Add handlers to root logger
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)

        if app:
            app.logger.handlers = root_logger.handlers
            app.logger.setLevel(log_level)
            app.logger.info("Logging configured for development mode")

    # Set levels for noisy third-party loggers
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('firebase_admin').setLevel(logging.WARNING)

    return root_logger


def get_logger(name):
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    logger = logging.getLogger(name)
    # Add request ID filter if not already present
    if not any(isinstance(f, RequestIdFilter) for f in logger.filters):
        logger.addFilter(RequestIdFilter())
    return logger


def log_execution_time(logger=None):
    """
    Decorator to log function execution time.

    Usage:
        @log_execution_time(logger)
        def my_function():
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger or logging.getLogger(func.__module__)
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                elapsed_time = time.time() - start_time
                _logger.info(
                    f"{func.__name__} completed successfully in {elapsed_time:.3f}s"
                )
                return result
            except Exception as e:
                elapsed_time = time.time() - start_time
                _logger.error(
                    f"{func.__name__} failed after {elapsed_time:.3f}s: {str(e)}",
                    exc_info=True
                )
                raise
        return wrapper
    return decorator


def log_exception(logger, message="An exception occurred", exc_info=None):
    """
    Log an exception with full traceback.

    Args:
        logger: Logger instance
        message: Custom error message
        exc_info: Exception info (sys.exc_info() or True)
    """
    if exc_info is None or exc_info is True:
        exc_info = sys.exc_info()

    logger.error(message, exc_info=exc_info)

    # Also log the full traceback as a separate message for clarity
    if exc_info and exc_info[0] is not None:
        tb_str = ''.join(traceback.format_exception(*exc_info))
        logger.error(f"Full traceback:\n{tb_str}")


def log_api_call(logger, api_name, params=None, response=None, error=None, duration=None):
    """
    Log API call details in a structured format.

    Args:
        logger: Logger instance
        api_name: Name of the API being called
        params: Request parameters (dict)
        response: Response data (dict)
        error: Error message if call failed
        duration: Call duration in seconds
    """
    log_data = {
        'api': api_name,
        'params': params or {},
        'duration': f"{duration:.3f}s" if duration else None,
    }

    if error:
        log_data['error'] = str(error)
        logger.error(f"API call failed: {log_data}")
    else:
        if response:
            log_data['response_size'] = len(str(response)) if response else 0
        logger.info(f"API call successful: {log_data}")


# Module-level logger for this file
logger = get_logger(__name__)
