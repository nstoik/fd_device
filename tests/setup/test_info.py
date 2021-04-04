"""Test the info module.

TODO: add tests for get_ip_of_interface, get_service_status
"""
import pytest

from fd_device.system.info import (
    get_cpu_temperature,
    get_device_name,
    get_serial,
    get_storage,
    get_system_data,
    get_system_memory,
    get_uptime,
    get_uptime_seconds,
)


@pytest.mark.usefixtures("tables")
def test_get_uptime():
    """Test the get_uptime function."""

    uptime = get_uptime()

    assert isinstance(uptime, str)
    assert len(uptime) > 0


@pytest.mark.usefixtures("tables")
def test_get_uptime_seconds():
    """Test the get_uptime_seconds function."""

    uptime_seconds = get_uptime_seconds()

    assert isinstance(uptime_seconds, int)
    assert uptime_seconds > 0


@pytest.mark.usefixtures("tables")
def test_get_cpu_temperature():
    """Test the get_CPU_temperature function."""

    cpu_temp = get_cpu_temperature()

    assert isinstance(cpu_temp, float)


@pytest.mark.usefixtures("tables")
def test_get_device_name():
    """Test the get_device_name function."""

    device_name = get_device_name()

    assert isinstance(device_name, str)


@pytest.mark.usefixtures("tables")
def test_get_serial():
    """Test the get_serial function."""

    serial = get_serial()

    assert isinstance(serial, str)
    assert len(serial) == 16


@pytest.mark.usefixtures("tables")
def test_get_system_data():
    """Test the get_system_data function."""

    data = get_system_data()

    assert isinstance(data, dict)
    assert "uptime" in data
    assert "current_time" in data
    assert "load_avg" in data
    assert "cpu_temp" in data


@pytest.mark.usefixtures("tables")
def test_get_system_memory():
    """Test get_system_memory function."""

    data = get_system_memory()

    assert isinstance(data, dict)
    assert "ram_used" in data
    assert "ram_total" in data
    assert "ram_free" in data
    assert "disk_used" in data
    assert "disk_total" in data
    assert "disk_free" in data


@pytest.mark.usefixtures("tables")
def test_get_storage():
    """Test get_storage function."""

    data = get_storage()

    assert isinstance(data, dict)
    assert "disk_used" in data
    assert "disk_free" in data
    assert "disk_total" in data
