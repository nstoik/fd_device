"""The network template files for configuring the device."""
import subprocess


def hostapd_file(interface, wifi_ssid, wifi_password):
    """Create a hostapd file at /etc/hostapd/hostapd.conf."""

    contents = (
        "# This is the name of the WiFi interface\n"
        "interface={interface}\n"
        "\n"
        "# Use the nl80211 driver with the brcmfmac driver\n"
        "driver=nl80211\n"
        "\n"
        "# This is the name of the network\n"
        "ssid={wifi_ssid}\n"
        "\n"
        "# Use the 2.4Ghz band\n"
        "hw_mode=g\n"
        "\n"
        "# Use channel 6\n"
        "channel=6\n"
        "\n"
        "# Enable 802.11n\n"
        "ieee80211n=1\n"
        "\n"
        "# Enable WMM\n"
        "wmm_enabled=1\n"
        "\n"
        "# Enable 40Mhz channels with 20ns guard interval\n"
        "ht_capab=[HT40][SHORT-GI-20]\n"
        "\n"
        "# Accept all MAC addresses\n"
        "macaddr_acl=0\n"
        "\n"
        "# Use WPA authentication\n"
        "auth_algs=1\n"
        "\n"
        "# Require clients to know the network name\n"
        "ignore_broadcast_ssid=0\n"
        "\n"
        "# Use WPA2\n"
        "wpa=2\n"
        "\n"
        "# Use a pre-shared key\n"
        "wpa_key_mgmt=WPA-PSK\n"
        "\n"
        "# The network passphrase\n"
        "wpa_passphrase={wifi_password}\n"
        "\n"
        "# Use AES, instead of TKIP\n"
        "rsn_pairwise=CCMP\n"
    ).format(interface=interface, wifi_ssid=wifi_ssid, wifi_password=wifi_password)

    with open("/tmp/hostapd_temp", "w") as f:
        f.write(contents)

    command = ["sudo", "mv", "/tmp/hostapd_temp", "/etc/hostapd/hostapd.conf"]
    subprocess.check_call(command)


def interface_file(wlan0_dhcp=True, wlan1_dhcp=True):
    """Create an interfaces file at /etc/network/interface."""

    # templates for dhcp and static
    wlan_dhcp = (
        "allow-hotplug {interface}\n"
        "iface {interface} inet dhcp\n"
        "    wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf\n"
        "\n"
    )

    wlan_static = (
        "allow-hotplug {interface}\n"
        "iface {interface} inet static\n"
        "        pre-up iptables-restore < /etc/iptables.ipv4.nat \n"
        "    address 10.10.1.1\n"
        "    netmask 255.255.255.0\n"
        "    network 10.10.1.0\n"
        "    broadcast 10.10.1.255\n"
        "\n"
    )

    joined_contents = []

    contents = (
        "# Include files from /etc/network/interfaces.d:\n"
        "source-directory /etc/network/interfaces.d\n"
        "\n"
        "auto lo\n"
        "iface lo inet loopback\n"
        "\n"
        "auto eth0\n"
        "iface eth0 inet dhcp\n"
        "\n"
    )

    joined_contents.append(contents)
    # build the string for wlan0. Either dhcp or static
    if wlan0_dhcp:
        joined_contents.append(wlan_dhcp.format(interface="wlan0"))
    else:
        joined_contents.append(wlan_static.format(interface="wlan0"))

    # build the string for wlan0. Either dhcp or static
    if wlan1_dhcp:
        joined_contents.append(wlan_dhcp.format(interface="wlan1"))
    else:
        joined_contents.append(wlan_static.format(interface="wlan1"))

    # compile all the joined_contents into one string and write it to file
    with open("/tmp/interface_temp", "w") as f:
        f.write("".join(joined_contents))

    command = ["sudo", "mv", "/tmp/interface_temp", "/etc/network/interfaces"]
    subprocess.check_call(command)


def iptables_file(external_interface, internal_interface, flush_only=False):
    """Create an iptables file at /etc/iptables.ipv4.nat."""

    command = ["sudo", "iptables", "--flush"]
    subprocess.check_call(command)

    command = ["sudo", "iptables", "--flush", "-t", "nat"]
    subprocess.check_call(command)

    # flush_only allows the iptables to be cleared (wpa only mode)
    if not flush_only:
        command = [
            "sudo",
            "iptables",
            "-t",
            "nat",
            "-A",
            "POSTROUTING",
            "-o",
            external_interface,
            "-j",
            "MASQUERADE",
        ]
        subprocess.check_call(command)

        command = [
            "sudo",
            "iptables",
            "-A",
            "FORWARD",
            "-i",
            external_interface,
            "-o",
            internal_interface,
            "-m",
            "state",
            "--state",
            "RELATED,ESTABLISHED",
            "-j",
            "ACCEPT",
        ]
        subprocess.check_call(command)

        command = [
            "sudo",
            "iptables",
            "-A",
            "FORWARD",
            "-i",
            internal_interface,
            "-o",
            external_interface,
            "-j",
            "ACCEPT",
        ]
        subprocess.check_call(command)

    command = ["sudo", "iptables-save"]
    with open("/tmp/iptables.ipv4.nat", "w") as f:
        subprocess.call(command, stdout=f)

    command = ["sudo", "mv", "/tmp/iptables.ipv4.nat", "/etc/iptables.ipv4.nat"]
    subprocess.check_call(command)


def dnsmasq_file(interface):
    """Create a dnsmasq file at '/etc/dnsmasq.conf'."""

    contents = (
        "interface={interface}           # Use interface {interface}\n"
        "listen-address=10.10.1.1        # Explicitly specifiy the address to listen on\n"
        "bind-interfaces                 # Bind to the interface\n"
        "server=8.8.8.8                  # Forward DNS requests to Google DNS\n"
        "domain-needed                   # Dont forward short names\n"
        "bogus-priv                      # Never forward addresses in non-routed space\n"
        "dhcp-range=10.10.1.50,10.10.1.150,12h"
    ).format(interface=interface)

    with open("/tmp/dnsmasq_temp", "w") as f:
        f.write(contents)

    command = ["sudo", "mv", "/tmp/dnsmasq_temp", "/etc/dnsmasq.conf"]
    subprocess.check_call(command)


def dhcpcd_file(interface=None):
    """Create a dhcpcd file at '/etc/dhcpcd.conf'."""

    top_part = (
        "# Inform the DHCP server of our hostname for DDNS.\n"
        "hostname\n"
        "\n"
        "# Use the hardware address of the interface for the Client ID.\n"
        "clientid\n"
        "\n"
        "# Persist interface configuration when dhcpcd exits.\n"
        "persistent\n"
        "\n"
        "option rapid_commit\n"
        "\n"
        "# A list of options to request from the DHCP server.\n"
        "option domain_name_servers, domain_name, domain_search, host_name\n"
        "option classless_static_routes\n"
        "# Most distributions have NTP support.\n"
        "option ntp_servers\n"
        "\n"
        "# A ServerID is required by RFC2131.\n"
        "require dhcp_server_identifier\n"
        "\n"
        "# Generate Stable Private IPv6 Addresses instead of hardware based ones\n"
        "slaac private\n"
        "\n"
        "# A hook script is provided to lookup the hostname if not set by the DHCP\n"
        "# server, but it should not be run by default.\n"
        "nohook lookup-hostname\n"
        "\n"
    )

    contents = []
    contents.append(top_part)

    if interface:
        contents.append("denyinterfaces {interface}\n".format(interface=interface))

    # compile all the contents into one string and write it to file
    with open("/tmp/dhcpcd_temp", "w") as f:
        f.write("".join(contents))

    command = ["sudo", "mv", "/tmp/dhcpcd_temp", "/etc/dhcpcd.conf"]
    subprocess.check_call(command)


def wpa_supplicant_file(networks):
    """Create a wpa supplicant file at '/etc/wpa_supplicant/wpa_supplicant.conf'.

    networks is a list of networks with a 'ssid' and 'password' entry
    """

    network_ssid = (
        "network={{\n"
        '   ssid="{ssid}"\n'
        '   psk="{password}"\n'
        "   key_mgmt=WPA-PSK\n"
        "}}\n"
        "\n"
    )

    header = (
        "ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n"
        "update_config=1\n"
        "country=CA\n"
        "\n"
    )

    contents = []
    contents.append(header)

    # go through all the networks
    for network in networks:
        contents.append(
            network_ssid.format(ssid=network["ssid"], password=network["password"])
        )

    # compile all the contents into one string and write it to file
    with open("/tmp/wpa_supplicant_temp", "w") as f:
        f.write("".join(contents))

    command = [
        "sudo",
        "mv",
        "/tmp/wpa_supplicant_temp",
        "/etc/wpa_supplicant/wpa_supplicant.conf",
    ]
    subprocess.check_call(command)
