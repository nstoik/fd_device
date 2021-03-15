"""Main command line interface entry point."""
import click

from .db import commands as db_commands
from .manage import commands as manage_commands
from .testing import commands as testing_commands


@click.group()
def entry_point():
    """Entry point for CLI."""


entry_point.add_command(manage_commands.first_setup)

entry_point.add_command(testing_commands.test)
entry_point.add_command(testing_commands.lint)

entry_point.add_command(db_commands.create_tables)
entry_point.add_command(db_commands.create_revision)
entry_point.add_command(db_commands.database_upgrade)
