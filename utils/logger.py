# logger.py
import logging

def get_logger(name):
    """
    Configures and returns a logger instance.

    Args:
        name (str): Name of the logger to create. Typically __name__ is passed from the caller.

    Returns:
        logging.Logger: Configured logger instance.
    """
    # Create a logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)  # Set the logging level

    # Create a console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add formatter to ch
    ch.setFormatter(formatter)

    # Add ch to logger
    if not logger.handlers:
        logger.addHandler(ch)

    return logger
