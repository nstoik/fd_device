"""Test device models."""
import datetime as dt

import pytest

from fd_device.database.device import Connection, Device

from .factories import DeviceFactory


@pytest.mark.usefixtures("tables")
class TestConnection:
    """Connection model tests."""

    @staticmethod
    def test_create_connection_object(dbsession):
        """Create a Connection instance."""

        connection = Connection()
        connection.save(dbsession)

        assert connection.last_updated is None
        assert isinstance(connection.first_connected, dt.datetime)
        assert not bool(connection.is_connected)

    @staticmethod
    def test_update_connection_object(dbsession):
        """Create and update a Connection instance."""

        connection = Connection()
        connection.save(dbsession)

        connection.is_connected = True
        connection.save(dbsession)

        assert isinstance(connection.last_updated, dt.datetime)
        assert bool(connection.is_connected)


@pytest.mark.usefixtures("tables")
class TestDevice:
    """Device model tests."""

    @staticmethod
    def test_create_device_object(dbsession):
        """Create a Device instance."""

        device = Device(device_id="TEST01")
        device.save(dbsession)

        assert device.__repr__() == "<Device: device_id=TEST01>"
        assert device.device_id == "TEST01"
        assert device.interior_sensor == "null"
        assert device.exterior_sensor == "null"

    @staticmethod
    def test_get_device_by_id(dbsession):
        """Test retrieving a device by its ID."""

        device = Device(device_id="TEST01")
        device.save(dbsession)

        retrieved = Device.get_by_id(device.id)

        assert device.id == retrieved.id

    @staticmethod
    def test_device_factory(dbsession):
        """Test DeviceFactory."""

        device = DeviceFactory.create(dbsession)
        device.save(dbsession)

        retrieved = Device.get_by_id(device.id)

        assert device.id == retrieved.id

    @staticmethod
    def test_device_properties(dbsession):
        """Test all Device properties."""

        device = DeviceFactory.create(dbsession)
        device.save(dbsession)

        assert device.hardware_version is None
        assert device.software_version is None
        assert isinstance(device.creation_time, dt.datetime)
        assert isinstance(device.last_updated, dt.datetime)
        assert device.interior_sensor == "null"
        assert device.exterior_sensor == "null"
        assert device.interior_temp is None
        assert device.exterior_temp is None
        assert device.grainbin_count == 0
        assert device.grainbins == []
