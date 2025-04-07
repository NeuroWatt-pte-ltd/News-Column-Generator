import logging 
import os
from dotenv import load_dotenv

def setup_logger(name: str):
    """
    Set up a logger instance with the specified name.

    :param name: The name of the logger.
    :return: A configured logger instance.
    """

    # Load environment variable, including the log level
    load_dotenv()
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Create a logger and set its logging level
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # If the logger already has handers, return it directly
    if logger.handlers:
        return logger 

    # Create a stream handler, set its format and logging level
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - [%(name)s] - %(message)s")
    )
    handler.setLevel(log_level)

    # Add the handler to the logger
    logger.addHandler(handler)

    # Prevent log propagation
    logger.propagate = False 

    return logger
