import logging
import os
import sys

_logging_configured = False

def setup_logging():
    global _logging_configured
    if _logging_configured:
        return

    log_dir = os.path.dirname(__file__)
    if not log_dir: 
        log_dir = os.getcwd() # Fallback if __file__ is not defined (e.g. interactive)
    LOG_FILE_PATH = os.path.join(log_dir, 'realtime_mrs.log')

    root_logger = logging.getLogger() 
    if root_logger.hasHandlers():
        for handler in list(root_logger.handlers): # Iterate over a copy
            root_logger.removeHandler(handler)
            handler.close()
        
    root_logger.setLevel(logging.DEBUG) # Set root logger to DEBUG to capture all levels

    formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')

    try:
        file_handler = logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)  # File handler logs INFO and above
        root_logger.addHandler(file_handler)
    except Exception as e:
        print(f"Critical Error: Could not set up file logger at {LOG_FILE_PATH}. Error: {e}", file=sys.stderr)

    stream_handler = logging.StreamHandler(sys.stdout) 
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.INFO) # Console logs INFO and above
    root_logger.addHandler(stream_handler)

    _logging_configured = True
    logging.getLogger("LoggerSetup").info(f"Logging configured. Root level: DEBUG, File/Console level: INFO. Log file: {LOG_FILE_PATH}")

def get_logger(name):
    setup_logging()
    logger = logging.getLogger(name)
    # Ensure module-specific loggers also propagate if their level isn't explicitly set lower than root
    # This is usually handled by default if not set, but being explicit can help in some complex scenarios.
    # For now, relying on root logger's level and handler levels.
    return logger 