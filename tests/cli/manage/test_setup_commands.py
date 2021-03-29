"""Test the setup_commands module."""
import pytest
from click.testing import CliRunner

from fd_device.cli.manage.setup_commands import first_setup
from fd_device.database.system import SystemSetup


@pytest.mark.usefixtures("tables")
class TestSetupCommands:
    """Setup_commands module tests."""

    @staticmethod
    def test_first_setup_execution():
        """Test that first_setup starts and executes."""

        runner = CliRunner()
        result = runner.invoke(first_setup)

        assert "First time setup" in result.output

    @staticmethod
    def test_first_setup_already_completed(dbsession):
        """Test that the cli command detects if setup already done."""

        # explicitly set the first_setup to true.
        system = SystemSetup()
        system.first_setup = True
        system.save(dbsession)

        runner = CliRunner()
        result = runner.invoke(first_setup, input="N\n")

        assert not result.exception
        assert "Setup has already been run" in result.output

    @staticmethod
    def test_first_setup_standalone_no_to_all():
        """Test standalone flag passed in."""

        runner = CliRunner()
        result = runner.invoke(
            first_setup, args="--standalone", input="N\nN\nN\nN\nN\n"
        )

        assert "Do you want to change the device name?" in result.output
        assert not result.exception
