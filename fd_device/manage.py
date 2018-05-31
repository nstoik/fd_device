import click

from fd_device.database.commands import create_tables, create_revision, database_upgrade
from fd_device.commands import first_setup

@click.group()
def cli():
    """Main entry point for farm device"""

@cli.command()
def run():
    """Run the farm device."""
    click.echo("Starting farm device")
    from .main import main
    main()

cli.add_command(create_tables)
cli.add_command(first_setup)
cli.add_command(create_revision)
cli.add_command(database_upgrade)
