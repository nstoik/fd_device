"""Module for all database commands."""
import click
from alembic import command as al_command
from alembic.config import Config as AlConfig

from fd_device.settings import get_config

@click.command("create_tables")
def create_tables():
    """
    create all database tables for first time setup
    """
    click.echo("create database")
    from fd_device.database.base import create_all_tables
    from fd_device.system import Hardware
    from fd_device.device import Device
    create_all_tables()
    click.echo("done")


@click.command("create_revision")
@click.option('--message', prompt='Provide a message for the revision', help='Message for revision')
def create_revision(message):
    """
    create a database migration using alembic
    """

    config = get_config()
    alembic_cnf = AlConfig(config.PROJECT_ROOT + '/alembic.ini')
    alembic_cnf.set_main_option('script_location', config.PROJECT_ROOT + '/migrations')

    al_command.revision(alembic_cnf, message=message, autogenerate=True)


@click.command("database_upgrade")
@click.option('--revision', default='head', prompt='What revision to upgrade to?', help='What revision to upgrade to')
def database_upgrade(revision):
    """
    upgrade database to given revision
    """

    config = get_config()
    alembic_cnf = AlConfig(config.PROJECT_ROOT + '/alembic.ini')
    alembic_cnf.set_main_option('script_location', config.PROJECT_ROOT + '/migrations')

    al_command.upgrade(alembic_cnf, revision)
