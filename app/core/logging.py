"""
Structured Logging Configuration
================================
Configures structlog for JSON-standardized logging in production.
Integrates with standard Python logging for library compatibility.
"""

import sys
import logging
import structlog
from app.core.config import settings


def setup_logging():
    """
    Initializes structlog with JSON rendering for production and 
    Console rendering for development.
    """
    
    # Standard library configuration
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )

    processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_production:
        # JSON logs for ELK/CloudWatch in production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty printing for development
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger(__name__)
