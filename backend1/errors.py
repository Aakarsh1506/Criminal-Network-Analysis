import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class APIError(Exception):
    def __init__(self, message, status=500, *, clear_cookie=False):
        super().__init__(message)
        self.message = message
        self.status = status
        self.clear_cookie = clear_cookie


@contextmanager
def api_errors(message):
    """Keep database/provider exceptions out of the public error response."""
    try:
        yield
    except APIError:
        raise
    except Exception:
        logger.exception(message)
        raise APIError(message) from None
