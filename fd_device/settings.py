import os
import logging

class Config(object):
    """Base configuration."""

    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))

    PRESENCE_PORT = 5554
    LOG_LEVEL = logging.INFO
    LOG_FILE = "/home/pi/farm_monitor/fl/farm_device.log"

    RMQ_USER = 'fm'
    RMQ_USER_PASSWORD = 'farm_monitor'

    UPDATER_PATH = "/home/pi/farm_monitor/farm_update/update.sh"

    SQLALCHEMY_DATABASE_URI = 'sqlite:////home/pi/farm_monitor/fd/fd_database.db'


class DevConfig(Config):
    """Development configuration."""

    DEBUG = True
    LOG_LEVEL = logging.DEBUG


class ProdConfig(Config):
    """Production configuration."""

    DEBUG = False
    LOG_LEVEL = logging.ERROR


class TestConfig(Config):
    """Test configuration."""

    DEBUG = True
    TESTING = True

    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'


def get_config():

    environment = os.environ.get("FD_DEVICE_CONFIG", default='dev')

    if environment == 'dev':
        return DevConfig
    elif environment == 'prod':
        return ProdConfig
    elif environment == 'test':
        return TestConfig
    else:
        return DevConfig
