"""Module for all database commands."""
import click
from alembic import command as al_command
from alembic.config import Config as AlConfig

from fd_device.database.base import create_all_tables

# import all models so they are available to the SqlAlchemy base
# pylint: disable=unused-import
from fd_device.database.device import Device  # noqa: F401
from fd_device.database.system import Hardware  # noqa: F401
from fd_device.settings import get_config


@click.group()
def database():
    """Command group for database commands."""


@database.command("create_tables")
def create_tables():
    """Create all database tables for first time setup."""
    click.echo("creating all tables")

    create_all_tables()

    config = get_config()
    alembic_cnf = AlConfig(config.PROJECT_ROOT + "/migrations/alembic.ini")
    alembic_cnf.set_main_option("script_location", config.PROJECT_ROOT + "/migrations")
    click.echo("stamping alembic head")
    al_command.stamp(alembic_cnf, "head")
    click.echo("done")


@database.command("create_revision")
@click.option(
    "--message",
    prompt="Provide a message for the revision",
    help="Message for revision",
)
def create_revision(message):
    """Create a database migration using alembic."""

    config = get_config()
    alembic_cnf = AlConfig(config.PROJECT_ROOT + "/migrations/alembic.ini")
    alembic_cnf.set_main_option("script_location", config.PROJECT_ROOT + "/migrations")

    al_command.revision(alembic_cnf, message=message, autogenerate=True)


@database.command("database_upgrade")
@click.option(
    "--revision",
    default="head",
    prompt="What revision to upgrade to?",
    help="What revision to upgrade to",
)
def database_upgrade(revision):
    """Upgrade database to given revision."""

    config = get_config()
    alembic_cnf = AlConfig(config.PROJECT_ROOT + "/migrations/alembic.ini")
    alembic_cnf.set_main_option("script_location", config.PROJECT_ROOT + "/migrations")

    al_command.upgrade(alembic_cnf, revision)
