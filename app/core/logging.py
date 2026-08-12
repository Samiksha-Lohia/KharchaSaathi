import logging
import sys

# Production logging format
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Local list cache to verify alerts in unit tests
ADMIN_ALERTS = []

def setup_logging():
    """
    Configures standard structured logging for the application.
    """
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

logger = logging.getLogger("KharchaSaathi")

def alert_admin_on_error(error_message: str):
    """
    Dispatches a critical error alert.
    Logs to critical output and registers in test list.
    """
    logger.critical(f"[ADMIN_ALERT] CRITICAL PIPELINE EXCEPTION: {error_message}")
    ADMIN_ALERTS.append(error_message)
    
    # (Optional: Connect to Meta WhatsApp API to dispatch actual admin text alert here)
