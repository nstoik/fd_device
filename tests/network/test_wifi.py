"""Tests for the wifi module.

TODO: add tests for functions: refresh_interfaces, scan_wifi, wifi_info, wifi_ap_clients, wifi_dhcp_info,
      set_interfaces, set_ap_mode, set_wpa_mode
"""
import pytest

from fd_device.database.system import Interface, Wifi
from fd_device.network.wifi import add_wifi_network, delete_wifi_network


@pytest.mark.usefixtures("tables")
def test_add_wifi_network(dbsession):
    """Test the add_wifi_network function."""

    interface = Interface("wlan0")
    interface.state = "dhcp"
    interface.save(dbsession)

    wifi = add_wifi_network(wifi_name="TestWiFiName", wifi_password="password")

    dbsession.add(wifi)

    assert wifi.name == "TestWiFiName"
    assert wifi.password == "password"
    assert wifi.interface == interface
    assert wifi.mode == "dhcp"
    assert wifi in interface.credentials


@pytest.mark.usefixtures("tables")
def test_add_wifi_network_with_interface(dbsession):
    """Test the add_wifi_netwrok function passing in an Interface."""

    interface = Interface("wlan0")
    interface.state = "dhcp"
    interface.save(dbsession)

    wifi = add_wifi_network(
        wifi_name="TestWiFiName", wifi_password="password", interface=interface
    )

    assert wifi.name == "TestWiFiName"
    assert wifi.password == "password"
    assert wifi.interface.id == interface.id
    assert wifi.mode == "dhcp"
    assert wifi in interface.credentials


@pytest.mark.usefixtures("tables")
def test_add_wifi_network_no_interface():
    """Test the add_wifi_netwrok function with no valid interface."""

    wifi = add_wifi_network(wifi_name="TestWiFiName", wifi_password="password")

    assert wifi is None


@pytest.mark.usefixtures("populate_interfaces")
def test_delete_wifi_network(dbsession):
    """Test the delete_wifi_network function."""

    wifi = add_wifi_network(wifi_name="TestWiFiName", wifi_password="password")
    dbsession.add(wifi)

    confirmed_deleted = delete_wifi_network(wifi.id)
    retrieved = Wifi.get_by_id(wifi.id)

    assert retrieved is None
    assert confirmed_deleted


@pytest.mark.usefixtures("tables")
def test_delete_wifi_network_not_exisit():
    """Test the delete_wifi_network function when the WiFi instance does not exist."""

    confirm_deleted = delete_wifi_network("99")

    assert not confirm_deleted
