"""Test system models."""
import datetime as dt

import pytest

from fd_device.database.system import Hardware, Interface, Software, SystemSetup, Wifi


@pytest.mark.usefixtures("tables")
class TestSystemSetup:
    """SystemSetup model tests."""

    @staticmethod
    def test_create_systemsetup(dbsession):
        """Create a SystemSetup instance."""

        system_setup = SystemSetup()
        system_setup.save(dbsession)

        assert not bool(system_setup.first_setup)
        assert isinstance(system_setup.first_setup_time, dt.datetime)
        assert bool(system_setup.standalone_configuration)

    @staticmethod
    def test_get_system_setup_by_id(dbsession):
        """Retrieve a SystemSetup instance by id."""

        system_setup = SystemSetup()
        system_setup.save(dbsession)

        retrieved = SystemSetup.get_by_id(system_setup.id)
        assert retrieved.id == system_setup.id


@pytest.mark.usefixtures("tables")
class TestInterface:
    """Interface model tests."""

    @staticmethod
    def test_create_interface(dbsession):
        """Create a Interface instance."""
        interface = Interface("eth0")
        interface.save(dbsession)

        assert interface.interface == "eth0"
        assert bool(interface.is_active)
        assert not bool(interface.is_for_fm)
        assert not bool(interface.is_external)
        assert interface.state is None
        assert interface.credentials == []

    @staticmethod
    def test_interface_get_by_id(dbsession):
        """Retrieve an interface by the id."""
        interface = Interface("eth0")
        interface.save(dbsession)

        retrieved = Interface.get_by_id(interface.id)
        assert retrieved.id == interface.id


@pytest.mark.usefixtures("tables")
class TestWifi:
    """WiFi model tests."""

    @staticmethod
    def test_create_wifi(dbsession):
        """Create a WiFi instance."""
        wifi = Wifi()
        wifi.save(dbsession)

        assert wifi.name == "FarmMonitor"
        assert wifi.password == "raspberry"
        assert wifi.mode == "wpa"
        assert wifi.interface_id is None
        assert wifi.interface is None

    @staticmethod
    def test_create_wifi_with_interface(dbsession):
        """Create a WiFi instance with an interface."""
        interface = Interface("eth0")
        interface.save(dbsession)

        wifi = Wifi()
        wifi.interface = interface
        wifi.save(dbsession)

        assert wifi.interface == interface
        assert wifi.interface_id == interface.id

    @staticmethod
    def test_wifi_get_by_id(dbsession):
        """Test retrieving a WiFi instance by id."""
        wifi = Wifi()
        wifi.save(dbsession)

        retrieved = Wifi.get_by_id(wifi.id)

        assert retrieved.id == wifi.id


@pytest.mark.usefixtures("tables")
class TestHardware:
    """Hardware model tests."""

    @staticmethod
    def test_create_hardware(dbsession):
        """Create a Hardware instance."""
        hardware = Hardware()
        hardware.save(dbsession)

        assert hardware.device_name is None
        assert hardware.hardware_version is None
        assert hardware.serial_number is None
        assert hardware.interior_sensor is None
        assert hardware.exterior_sensor is None
        assert hardware.grainbin_reader_count == 0

    @staticmethod
    def test_hardware_get_by_id(dbsession):
        """Retrieve a Hardware instance by the id."""
        hardware = Hardware()
        hardware.save(dbsession)

        retrieved = Hardware.get_by_id(hardware.id)
        assert retrieved.id == hardware.id


@pytest.mark.usefixtures("tables")
class TestSoftware:
    """Software model tests."""

    @staticmethod
    def test_create_software(dbsession):
        """Create a Software instance."""
        software = Software()
        software.save(dbsession)

        assert software.software_version is None
        assert software.software_version_last is None

    @staticmethod
    def test_software_get_by_id(dbsession):
        """Retrieve a Software instance by the id."""
        software = Software()
        software.save(dbsession)

        retrieved = Software.get_by_id(software.id)
        assert retrieved.id == software.id
