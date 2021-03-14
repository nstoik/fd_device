import os
import logging

class CeleryConfig(object):
    """ Celery configuration """

    ## Broker settings.
    broker_url = 'pyamqp://fm:farm_monitor@localhost/farm_monitor'

    # List of modules to import when the Celery worker starts.
    # imports = ('fm_server.device.tasks',)

    ## Using the database to store task state and results.
    result_backend = 'rpc://'

    broker_transport_options = {'confirm_publish': True}

    broker_pool_limit = 0

class Config(object):
    """Base configuration."""

    APP_DIR = os.path.abspath(os.path.dirname(__file__))  # This directory
    PROJECT_ROOT = os.path.abspath(os.path.join(APP_DIR, os.pardir))

    PRESENCE_PORT = 5554

    LOG_LEVEL = logging.INFO
    LOG_FILE = "/logs/farm_device.log"

    UPDATER_PATH = "/home/pi/farm_monitor/farm_update/update.sh"

    SQLALCHEMY_DATABASE_URI = 'postgresql://fd:farm_device@fd_db/farm_device.db'

    RABBITMQ_USER = 'fd'
    RABBITMQ_PASSWORD = 'farm_monitor'
    RABBITMQ_VHOST = 'farm_monitor'


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


def get_config(override_default=None):
    """Return the Config option based on environment variables.

    If override_default is passed, that configuration is used instead.
    If there is no match or nothing set then the environment defaults to 'dev'.
    """

    if override_default is None:
        environment = os.environ.get("FD_DEVICE_CONFIG", default="dev")
    else:
        environment = override_default

    if environment == "dev":
        return DevConfig
    if environment == "prod":
        return ProdConfig
    if environment == "test":
        return TestConfig
    return DevConfig
