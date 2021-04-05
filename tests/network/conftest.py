"""Fixtures for the network module tests."""
# pylint: disable=unused-argument
import pytest

from fd_device.database.system import Interface


@pytest.fixture()
def populate_interfaces(tables, dbsession):
    """Populate interfaces into the database."""

    interface = Interface("wlan0")
    interface.is_active = True
    interface.is_for_fm = True
    interface.is_external = True
    interface.state = "dhcp"

    interface.save(dbsession)
