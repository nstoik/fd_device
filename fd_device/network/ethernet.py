"""Control the ethernet connections of the device."""
import logging
from typing import List

import netifaces
from netifaces import AF_INET

from fd_device.database.base import get_session
from fd_device.database.system import Interface

logger = logging.getLogger("fm.network.ethernet")


def ethernet_connected() -> bool:
    """Check if interface 'eth0 has an IP address.

    :return: True if the interface has an IP address, otherwise False.
    :rtype: bool
    """

    try:
        netifaces.ifaddresses("eth0")[AF_INET][0]
    except KeyError:
        return False

    return True


def get_interfaces(keep_wlan=True, keep_eth=True) -> List[str]:
    """Get the interfaces of the device.

    'lo' and 'sit0' interfaces areremoved from the return list if present.

    :param keep_wlan: If False, removes all interfaces that are not 'wlan', defaults to True
    :type keep_wlan: bool, optional
    :param keep_eth: If False, removes all interfaces that are not 'eth', defaults to True
    :type keep_eth: bool, optional
    :return: A list of interfaces present on the device with the filters applied.
    :rtype: List[str]
    """

    logger.debug("getting all interfaces")
    interfaces: List[str] = netifaces.interfaces()

    if "lo" in interfaces:
        interfaces.remove("lo")

    if "sit0" in interfaces:
        interfaces.remove("sit0")

    for x in interfaces:
        if not keep_wlan and x.startswith("wlan"):
            interfaces.remove(x)
        if not keep_eth and x.startswith("eth"):
            interfaces.remove(x)

    return interfaces


def get_external_interface() -> str:
    """Get the external interface.

    This is the interface that is used to send traffic out for any AP.
    First check if eth0 is present. Then check if there is a wlan
    interface that has a state of 'dhcp'

    :return: The name of the interface that is for external traffic, or 'None'
    :rtype: str
    """

    session = get_session()

    if ethernet_connected():
        ethernet = session.query(Interface).filter_by(interface="eth0").first()
        ethernet.is_external = True
        session.commit()
        session.close()
        return "eth0"

    # now check if it is either wlan0 or wlan1
    interfaces = session.query(Interface).filter_by(state="dhcp").all()

    for interface in interfaces:
        if interface.interface != "eth0":
            interface.is_external = True
            session.commit()
            session.close()
            return str(interface.interface)

    session.close()
    return "None"
