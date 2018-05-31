import subprocess
import logging
import netifaces
import time
from sqlalchemy.orm.exc import NoResultFound

from fd_device.database.base import get_session
from fd_device.database.system import Wifi, Interface
from fd_device.network.network_files import interface_file, dhcpcd_file, dnsmasq_file,\
    hostapd_file, wpa_supplicant_file, iptables_file
from fd_device.network.ethernet import get_interfaces, ethernet_connected, get_external_interface
from fd_device.settings import get_config

logger = logging.getLogger('fd.network.wifi')


def refresh_interfaces():
    """
    refresh all interfaces. Update with current information
    """

    session = get_session()
    ap_present = False

    interfaces = get_interfaces()

    # update all interfaces.active to be False by default
    session.query(Interface).update({Interface.is_active: False})

    for my_interface in interfaces:
        try:
            interface = session.query(Interface).filter_by(interface=my_interface).one()

            interface.is_active = True
            # see if there is an interface that is configured for an ap
            if interface.state == 'ap':
                ap_present = True

        # must be a new interface so lets add it
        except NoResultFound:
            new_interface = Interface(my_interface)
            new_interface.is_active = True
            new_interface.is_for_fm = False
            new_interface.state = 'dhcp'
            session.add(new_interface)

    session.commit()
    session.close()

    if ap_present:
        set_ap_mode()
    else:
        set_wpa_mode()

    return


def scan_wifi(interface=None):
    """
    Scan the interface for the available wifi networks.
    Returns a list of strings that are the found networks
    """

    # if no interface is given, try find an interface in the database
    # that has the state set to 'dhcp' and is not 'eth'
    if interface is None:
        session = get_session()

        interfaces = session.query(Interface).all()
        for x in interfaces:
            if not x.interface.startswith('eth'):
                if x.state == 'dhcp':
                    interface = x.interface
        
        session.close()

    # exit if still no interface
    if interface is None:
        logger.warn("No interface available to scan wifi networks")
        return []

    # scan the interface for networks
    command = ['sudo', 'iwlist', interface, 'scan']
    output = subprocess.check_output(command, universal_newlines=True)
    index = output.find('ESSID:"')
    ssid = []
    while index > 0:
        stop = output.find('"\n', index)

        ssid.append(output[index + 7: stop])

        output = output[stop + 2:]

        index = output.find('ESSID:"')

    return ssid


def add_wifi_network(wifi_name, wifi_password, interface=None):
    """
    Add a given wifi to the list of available wifi networks.
    """

    session = get_session()

    if interface is None:
        interfaces = session.query(Interface).all()
        for x in interfaces:
            # find first available wlan interface that is not dhcp
            if x.interface != 'eth0' and x.state == 'dhcp':
                interface = x.interface
                break


    if interface is None:
        logger.error("No interface available to add new wifi network")
        return None

    # have an interface. now create a Wifi entry
    new_wifi = Wifi()
    new_wifi.wifi_name = wifi_name
    new_wifi.wifi_password = wifi_password
    new_wifi.wifi_mode = 'dhcp'
    new_wifi.interface = interface

    session.add(new_wifi)
    session.commit()

    session.close()

    return new_wifi


def delete_wifi_network(id):
    """
    Delete a wifi network given by 'id'
    """

    session = get_session()

    session.query(Wifi).filter_by(id=id).delete()
    session.commit()

    session.close()

    return


def wifi_info():
    """
    Get a list of wifi details for all wlan interfaces
    For each interface, a dictionary of details is added to the list
    Keys of the dictionary are:
        interface: the interface
        if ap:
            clients: the number of clients currently connected
            ssid: the ssid of the ap
            password: the password of the ap
        if dhcp:
            state: either the SSID currently connected to or False
            state_boolean: boolean value for state. True or False
            if state:
                address: the IPV4 address
            ssid: the ssid of the dhcp interface
            password: the password of the dhcp interface
    """

    logger.debug("getting wifi information")

    wlan_interfaces = get_interfaces(only_wlan=True)

    wifi = []

    session = get_session()

    for w_interface in wlan_interfaces:
        try:
            info = {}
            interface = session.query(Interface).filter_by(interface=w_interface).one()
            info['interface'] = interface
            if interface.state == 'ap':
                info['clients'] = wifi_ap_clients(interface.interface)
                info['ssid'] = interface.credentials[0].wifi_name
                info['password'] = interface.credentials[0].wifi_password
            else:
                info['state'] = wifi_dhcp_info(interface.interface)
                if info['state'] is False:
                    info['state_boolean'] = False
                else:
                    info['state_boolean'] = True
                    if w_interface in netifaces.interfaces():
                        address = netifaces.ifaddresses(w_interface)
                        info['address'] = address[netifaces.AF_INET][0]['addr']

                if interface.credentials:
                    info['ssid'] = interface.credentials[0].wifi_name
                    info['password'] = interface.credentials[0].wifi_password

            wifi.append(info)

        except NoResultFound:
            pass

    session.close()
    return wifi


def wifi_ap_clients(interface):
    """
    Return the list of ap clients given an interface name
    """

    logger.debug("getting wifi clients")
    command = ['iw', 'dev', interface, 'station', 'dump']
    client_info = subprocess.check_output(command, universal_newlines=True)

    client_count = client_info.count("Station")

    return client_count


def wifi_dhcp_info(interface):
    """
    Returns the SSID that is connected for a given interface name
    else returns False
    """

    command = ['iw', interface, 'link']
    output = subprocess.check_output(command, universal_newlines=True)

    if output.startswith("Not connected."):
        return False

    else:
        start_index = output.find('SSID: ')
        end_index = output.find('\n', start_index)
        ssid = output[start_index + 6:end_index]

        return ssid


def set_interfaces(interfaces):
    """
    Set interface information into database and configure hardware
    accordingly
    interfaces is a list of dictionaries with required information
    """

    session = get_session()
    wifi_ap_present = False

    for interface in interfaces:
        try:
            db_result = session.query(Interface).filter_by(interface=interface['name']).one()
        except NoResultFound:
            db_result = Interface(interface['name'])
            session.add(db_result)
        db_result.is_active = True
        db_result.is_for_fm = interface['is_for_fm']
        db_result.state = interface['state']
        if interface['state'] == 'ap':
            wifi_ap_present = True
        if 'creds' in interface:
            set_wifi_credentials(session, db_result, interface['creds'])

    session.commit()

    if wifi_ap_present:
        set_ap_mode()
    else:
        set_wpa_mode()

    return


# sets the wifi credentials information for a given interface
def set_wifi_credentials(session, interface, wifi_creds):

    logger.info("adding wifi. name: {0} password: {1} state: {2}".format(wifi_creds['ssid'],
                                                                         wifi_creds['password'],
                                                                         interface.state))

    # see if the wifi credentials already exisit
    for credential in interface.credentials:
        if credential.wifi_name == wifi_creds['ssid']:
            logger.debug("ssid already exisits for {}. Updating.".format(interface.interface))
            credential.wifi_password = wifi_creds['password']
            credential.wifi_mode = interface.state
            return

    # else the wifi credentials do not exisit
    new_creds = Wifi()
    new_creds.interface = interface.interface
    new_creds.wifi_name = wifi_creds['ssid']
    new_creds.wifi_password = wifi_creds['password']
    new_creds.wifi_mode = interface.state
    session.add(new_creds)
    return


# perform all of the setup and intialization work for interfaces
# with an ap present
def set_ap_mode():

    logger.debug("setting wifi into ap mode")
    session = get_session()

    # get the wlan0 and wlan1 dhcp states
    try:
        ap_interface = session.query(Interface).filter_by(state='ap').first()
        ap_ssid = ap_interface.credentials[0].wifi_name
        ap_password = ap_interface.credentials[0].wifi_password

    except NoResultFound:
        # error. abort
        logger.warn("No interface with state set to 'ap'. Aborting")
        return

    # get info for interface file
    if ap_interface.interface == 'wlan0':
        wlan0_dhcp = False
        wlan1_dhcp = True

    else:
        wlan0_dhcp = True
        wlan1_dhcp = False

    # get the info for the wpa_supplicant file
    wifi_defs = session.query(Wifi).filter(Wifi.wifi_mode != 'ap').all()
    networks = []
    for wifi in wifi_defs:
        new_network = {}
        new_network['ssid'] = wifi.wifi_name
        new_network['password'] = wifi.wifi_password
        networks.append(new_network)

    # get the information for the iptables_file
    internal_interface = ap_interface.interface
    external_interface = get_external_interface()

    iptables_file(external_interface, internal_interface)
    interface_file(wlan0_dhcp=wlan0_dhcp, wlan1_dhcp=wlan1_dhcp)
    wpa_supplicant_file(networks)
    dhcpcd_file(interface=ap_interface.interface)
    dnsmasq_file(interface=ap_interface.interface)
    hostapd_file(ap_interface.interface, ap_ssid, ap_password)

    config = get_config()

    path = config.APP_DIR + '/network/ap_script.sh'

    command = ['sudo', 'sh', path, ap_interface.interface]
    subprocess.check_call(command)

    session.close()
    return


# perform all of the setup and intialization work for interfaces
# with no ap present
def set_wpa_mode():

    logger.debug("setting all wlan into wpa mode")
    session = get_session()

    # get the info for the wpa_supplicant file
    wifi_defs = session.query(Wifi).filter(Wifi.wifi_mode != 'ap').all()
    networks = []
    for wifi in wifi_defs:
        new_network = {}
        new_network['ssid'] = wifi.wifi_name
        new_network['password'] = wifi.wifi_password
        networks.append(new_network)

    iptables_file(None, None, flush_only=True)
    interface_file()
    wpa_supplicant_file(networks)
    dhcpcd_file()

    config = get_config()
    path = config.APP_DIR + '/network/wpa_script.sh'

    command = ['sudo', 'sh', path]
    subprocess.check_call(command)
    session.close()
    return
