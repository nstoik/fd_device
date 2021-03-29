"""Module for all database commands."""
import click
from alembic import command as al_command
from alembic.config import Config as AlConfig

from fd_device.database.base import (
    create_all_tables,
    drop_all_tables,
    get_base,
    get_session,
)

# import all models so they are available to the SqlAlchemy base
# pylint: disable=unused-import
from fd_device.database.device import Device  # noqa: F401
from fd_device.database.system import Hardware  # noqa: F401
from fd_device.settings import get_config


@click.group()
def database():
    """Command group for database commands."""


@database.command()
@click.option(
    "--confirm",
    default=False,
    is_flag=True,
    help="Confirm this action. This will delete all previous database data.",
)
def delete_all_data(confirm):
    """Delete all data from the database."""

    if not confirm:
        click.echo(
            "Action was not confirmed (command option '--confirm'). No change made."
        )
    else:
        click.echo("deleting all data from the database.")

        base = get_base()
        session = get_session()
        for table in reversed(base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()

        click.echo("done")


@database.command()
@click.pass_context
def recreate_database(ctx):
    """Drop and recreate database tables."""

    click.echo("dropping all tables")
    drop_all_tables()
    ctx.forward(create_tables)


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
