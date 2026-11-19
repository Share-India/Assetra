import os
import re
import logging
from logging.handlers import RotatingFileHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

APP_LOG_FILE = os.path.join(LOGS_DIR, "app.log")
ERROR_LOG_FILE = os.path.join(LOGS_DIR, "error.log")

# Patterns that must never appear in application or error logs
_SENSITIVE_PATTERNS = [
    (re.compile(r'(?i)("?(?:password|current_password|new_password|confirm_password|credential|token|access_token|reset_token|google_reauth_token|turnstile_token|secret|api_key)"?\s*[:=]\s*)"[^"]*"'), r'\1"[REDACTED]"'),
    (re.compile(r"(?i)('?(?:password|current_password|new_password|confirm_password|credential|token|access_token|reset_token|google_reauth_token|turnstile_token|secret|api_key)'?\s*[:=]\s*)'[^']*'"), r"\1'[REDACTED]'"),
    (re.compile(r"(?i)(Bearer\s+)[A-Za-z0-9\-._~+/]+=*"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(access_token=)[^;\s&]+"), r"\1[REDACTED_COOKIE]"),
]


def redact_sensitive_text(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    cleaned = text
    for env_var in ("GEMINI_API_KEY", "JWT_SECRET", "SMTP_PASSWORD", "DB_PASSWORD", "TURNSTILE_SECRET"):
        val = os.getenv(env_var, "").strip()
        if val and len(val) >= 4:
            cleaned = cleaned.replace(val, f"[REDACTED_{env_var}]")
    for pattern, repl in _SENSITIVE_PATTERNS:
        cleaned = pattern.sub(repl, cleaned)
    return cleaned


class SafeLogFilter(logging.Filter):
    """Filter that intercepts and scrubs secrets, passwords, tokens, cookies, and API keys from all log records."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_sensitive_text(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: (redact_sensitive_text(v) if isinstance(v, str) else v)
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    (redact_sensitive_text(arg) if isinstance(arg, str) else arg)
                    for arg in record.args
                )
        return True


def setup_logging() -> logging.Logger:
    """
    Configure rotating file handlers for logs/app.log and logs/error.log plus console output.
    Idempotent across module reloads.
    """
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"
    log_level = getattr(logging, log_level_name, logging.INFO)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    safe_filter = SafeLogFilter()

    # 1. Rotating handler for logs/app.log (10 MB per file, keep 5 backups)
    app_file_handler = RotatingFileHandler(
        APP_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    app_file_handler.setLevel(log_level)
    app_file_handler.setFormatter(formatter)
    app_file_handler.addFilter(safe_filter)

    # 2. Rotating handler for logs/error.log (ERROR and CRITICAL only, 10 MB per file, keep 5 backups)
    error_file_handler = RotatingFileHandler(
        ERROR_LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)
    error_file_handler.addFilter(safe_filter)

    # 3. Console stream handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(safe_filter)

    # Close any existing handlers on root before replacing
    for h in list(logging.root.handlers):
        try:
            h.close()
        except Exception:
            pass

    logging.root.handlers = [app_file_handler, error_file_handler, console_handler]
    logging.root.setLevel(log_level)

    logger = logging.getLogger("far_backend")
    logger.setLevel(log_level)
    logger.propagate = True
    return logger

