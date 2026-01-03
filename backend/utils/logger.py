"""
Structured Logging Utilities for AIcineDB Backend
Implements structured logging with context and request tracking
"""
import logging
import sys
import json
from typing import Any, Dict, Optional
from datetime import datetime
from contextvars import ContextVar
import uuid

# Context variable for request ID (thread-safe)
request_id_context: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.
    
    Includes:
    - Timestamp
    - Log level
    - Logger name
    - Message
    - Request ID (if available)
    - Additional context fields
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON string with structured log data
        """
        # Base log structure
        log_data: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request ID if available
        request_id = request_id_context.get()
        if request_id:
            log_data["request_id"] = request_id
        
        # Add extra fields from record
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add file/line info in debug mode
        if record.levelno >= logging.WARNING:
            log_data["location"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        return json.dumps(log_data, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for development.
    
    Format: [TIMESTAMP] LEVEL: message (request_id=XXX)
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record in human-readable format"""
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        message = record.getMessage()
        
        # Build log string
        parts = [f"[{timestamp}]", f"{level}:", message]
        
        # Add request ID if available
        request_id = request_id_context.get()
        if request_id:
            parts.append(f"(request_id={request_id})")
        
        # Add location for errors
        if record.levelno >= logging.ERROR:
            parts.append(f"({record.pathname}:{record.lineno})")
        
        return " ".join(parts)


def setup_logging(
    level: str = "INFO",
    structured: bool = False,
    log_file: Optional[str] = None
) -> None:
    """
    Setup logging configuration for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: If True, use JSON structured logging, else human-readable
        log_file: Optional file path to write logs to
    """
    # Convert level string to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Remove existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    
    # Choose formatter based on mode
    if structured:
        formatter = StructuredFormatter()
    else:
        formatter = HumanReadableFormatter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    # Set root logger level
    root_logger.setLevel(log_level)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set request ID in context for current request.
    
    Args:
        request_id: Optional request ID, generates one if not provided
        
    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    
    request_id_context.set(request_id)
    return request_id


def get_request_id() -> Optional[str]:
    """
    Get current request ID from context.
    
    Returns:
        Current request ID or None if not set
    """
    return request_id_context.get()


def clear_request_id() -> None:
    """Clear request ID from context (call at end of request)"""
    request_id_context.set(None)


def log_event(
    logger: logging.Logger,
    event_type: str,
    message: str,
    level: str = "INFO",
    **extra_fields: Any
) -> None:
    """
    Log a structured event with additional context.
    
    Args:
        logger: Logger instance to use
        event_type: Type of event (e.g., "title_creation", "user_auth")
        message: Human-readable message
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        **extra_fields: Additional fields to include in structured log
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Add event type to extra fields
    extra_fields["event_type"] = event_type
    
    # Create log record with extra fields
    logger.log(
        log_level,
        message,
        extra=extra_fields
    )


# Convenience functions for common events

def log_authentication(
    logger: logging.Logger,
    user_id: str,
    user_email: str,
    success: bool,
    reason: Optional[str] = None
) -> None:
    """Log authentication event"""
    log_event(
        logger,
        event_type="user_authentication",
        message=f"Authentication {'successful' if success else 'failed'} for {user_email}",
        level="INFO" if success else "WARNING",
        user_id=user_id,
        user_email=user_email,
        success=success,
        reason=reason
    )


def log_title_creation(
    logger: logging.Logger,
    title_id: str,
    title: str,
    user_id: str,
    status: str
) -> None:
    """Log title creation event"""
    log_event(
        logger,
        event_type="title_creation",
        message=f"Title created: {title}",
        level="INFO",
        title_id=title_id,
        title=title,
        user_id=user_id,
        status=status
    )


def log_admin_action(
    logger: logging.Logger,
    action: str,
    admin_id: str,
    admin_email: str,
    target_resource: str,
    target_id: str,
    details: Optional[Dict[str, Any]] = None
) -> None:
    """Log admin action for audit trail"""
    log_event(
        logger,
        event_type="admin_action",
        message=f"Admin {admin_email} performed {action} on {target_resource}/{target_id}",
        level="INFO",
        action=action,
        admin_id=admin_id,
        admin_email=admin_email,
        target_resource=target_resource,
        target_id=target_id,
        details=details or {}
    )


def log_security_event(
    logger: logging.Logger,
    event: str,
    severity: str,
    details: Dict[str, Any]
) -> None:
    """Log security-related event"""
    log_event(
        logger,
        event_type="security_event",
        message=f"Security event: {event}",
        level=severity.upper(),
        event=event,
        severity=severity,
        **details
    )


# Example usage:
if __name__ == "__main__":
    # Development mode (human-readable)
    setup_logging(level="INFO", structured=False)
    
    logger = logging.getLogger(__name__)
    
    # Set request ID for context
    set_request_id("test-request-123")
    
    # Regular logging
    logger.info("Application started")
    
    # Structured event logging
    log_authentication(
        logger,
        user_id="user-123",
        user_email="test@example.com",
        success=True
    )
    
    log_title_creation(
        logger,
        title_id="title-456",
        title="My AI Film",
        user_id="user-123",
        status="pending"
    )
    
    # Clear request ID
    clear_request_id()
