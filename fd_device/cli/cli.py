"""Main command line interface entry point."""
import click

from .db import commands as db_commands
from .manage import commands as manage_commands
from .manage import setup_commands
from .testing import commands as testing_commands


@click.group()
def entry_point():
    """Entry point for CLI."""


entry_point.add_command(manage_commands.run)
entry_point.add_command(setup_commands.first_setup)

entry_point.add_command(testing_commands.test)
entry_point.add_command(testing_commands.lint)
entry_point.add_command(testing_commands.docstring)

entry_point.add_command(db_commands.database)
