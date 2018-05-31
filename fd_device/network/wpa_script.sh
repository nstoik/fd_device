#!/bin/bash
# example usage ./wpa_script.sh

systemctl stop hostapd.service dnsmasq.service
systemctl disable hostapd.service dnsmasq.service


ifdown wlan0
ifdown wlan1
sleep 5
ifup wlan0
ifup wlan1
