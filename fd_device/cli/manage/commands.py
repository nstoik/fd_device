"""Click commands for starting the app."""

import click

from fd_device.main import main


@click.command()
def run():
    """Run the server."""
    click.echo("Starting server.")
    main()
