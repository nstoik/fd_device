import logging

from fd_device.database.base import get_session
from .settings import get_config
from .tools.mp_logging import MultiProcessingLog, MultiProcessingLogStandardOutput
from .tools.startup import get_rabbitmq_address

def configure_logging(config):

    logger = logging.getLogger('fm')
    logfile_path = config.LOG_FILE
    log_level = config.LOG_LEVEL
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler = MultiProcessingLog(logfile_path, mode='a', maxsize=1024 * 1024, rotate=10)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(log_level)
    logger.propagate = False

    if log_level == logging.DEBUG:
        debug_handler = MultiProcessingLogStandardOutput()
        debug_handler.setFormatter(formatter)
        logger.addHandler(debug_handler)

    return logger

def main():

    config = get_config()
    logger = configure_logging(config)
    session = get_session()

    if not get_rabbitmq_address(logger, session):
        logger.warn("No address for rabbitmq server found")
    

if __name__ == '__main__':
    main()