# src/looplm/utils/warnings.py

import warnings
import logging
import os

def suppress_warnings():
    """Suppress all known warnings and configure logging."""
    # Disable all warnings by default
    if not os.getenv('LOOPLM_SHOW_WARNINGS'):
        warnings.filterwarnings('ignore')

    # Configure logging
    logging.basicConfig(level=logging.ERROR)

    # Suppress specific loggers
    for logger_name in ['httpx', 'litellm', 'pydantic']:
        logging.getLogger(logger_name).setLevel(logging.ERROR)

# Execute immediately on import
suppress_warnings()