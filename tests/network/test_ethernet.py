"""Tests for the ethernet module.

TODO: add test for get_external_interface
"""
from fd_device.network.ethernet import ethernet_connected, get_interfaces


def test_ethernet_connected():
    """Test the ethernet_connected function."""

    is_connected = ethernet_connected()

    assert isinstance(is_connected, bool)


def test_get_interfaces_default():
    """Test the get_interfaces function with default parameters."""

    interfaces = get_interfaces()

    assert isinstance(interfaces, list)
    assert "lo" not in interfaces
    assert "sit0" not in interfaces


def test_get_interfaces_no_eth():
    """Test the get_interfaces functions with no 'eth' interfaces."""

    interfaces = get_interfaces(keep_eth=False)

    for x in interfaces:
        assert not x.startswith("eth")


def test_get_interfaces_no_wlan():
    """Test the get_interfaces functions with no 'wlan' interfaces."""

    interfaces = get_interfaces(keep_wlan=False)

    for x in interfaces:
        assert not x.startswith("wlan")
