import logging
import time
from logging.handlers import RotatingFileHandler
from multiprocessing import Process

from multiprocessing_logging import install_mp_handler

from fd_device.database.base import get_session
from fd_device.device.service import run_connection
from .settings import get_config
from .tools.startup import get_rabbitmq_address

def configure_logging(config):

    logger = logging.getLogger('fd')
    logfile_path = config.LOG_FILE
    log_level = config.LOG_LEVEL

    logger.setLevel(log_level)
    logger.propagate = False

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_handler = RotatingFileHandler(logfile_path, mode='a', maxBytes=1024 * 1024, backupCount=10)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if log_level == logging.DEBUG:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    install_mp_handler(logger=logger)

    return logger

def main():

    config = get_config()
    logger = configure_logging(config)
    session = get_session()

    if not get_rabbitmq_address(logger, session):
        logger.error("No address for rabbitmq server found")
        time.sleep(1)
        return

    device_connection = Process(target=run_connection)
    device_connection.start()

    try:
        device_connection.join()
    except KeyboardInterrupt:
        logger.warn("Keyboard interrupt in main process")
        
        time.sleep(1)
        device_connection.terminate()
        device_connection.join()

    return
    

if __name__ == '__main__':
    main()