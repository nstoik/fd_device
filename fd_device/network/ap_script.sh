#!/bin/bash
# example usage ./ap_script.sh {INTERFACE}

INTERFACE=$1

# don't need to stop and disable these I think
# systemctl stop wpa_supplicant.service
# systemctl disable wpa_supplicant.service

# stop services just in case
systemctl stop hostapd.service dnsmasq.service


ifdown $INTERFACE
sleep 5
ifup $INTERFACE

systemctl start hostapd.service dnsmasq.service
systemctl enable hostapd.service dnsmasq.service
