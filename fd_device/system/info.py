"""Get information about the running system."""
import datetime
import logging
import os
import socket
import subprocess

import netifaces
import psutil

logger = logging.getLogger("fd.system.info")


def get_ip_of_interface(interface, broadcast=False):
    """Get the ip address of a given interface.

    If broadcast is true, get the broadcast address.
    """

    if not broadcast:
        ip = netifaces.ifaddresses(interface)[2][0]["addr"]

    else:
        ip = netifaces.ifaddresses(interface)[2][0]["broadcast"]

    return ip


def get_uptime():
    """Return the system uptime."""
    logger.debug("getting uptime")
    uptime = subprocess.check_output(["uptime", "-p"], universal_newlines=True)
    return str(uptime[3:])


def get_uptime_seconds():
    """Return the system uptime in seconds."""

    logger.debug("getting uptime in seconds")
    uptime = subprocess.check_output(["cat", "/proc/uptime"], universal_newlines=True)

    seconds = int(float(uptime.split()[0]))
    return seconds


def get_cpu_temperature():
    """Return the CPU temperature."""

    logger.debug("getting CPU temperature")
    filepath = "/sys/class/thermal/thermal_zone0/temp"
    res = subprocess.check_output(["cat", filepath], universal_newlines=True)
    return float(int(res) / 1000)


def get_service_status():
    """Return the status of the service."""
    # pylint: disable=unreachable
    raise NotImplementedError

    logger.debug("getting service status")
    command = ["sudo", "systemctl", "is-active", "farm-monitor.service"]
    status = ""
    try:
        status = subprocess.check_output(command, universal_newlines=True)
    except subprocess.CalledProcessError:
        pass

    return bool(status.startswith("active"))


def get_device_name():
    """Return the name of the device."""

    logger.debug("getting device name")
    device_name = socket.gethostname()
    return device_name


def getserial():
    """Return the serial number of the device."""

    logger.debug("getting serial number")
    # Extract serial
    cpuserial = "0000000000000000"
    try:
        # first try cpuinfo file
        f = open("/proc/cpuinfo", "r")
        for line in f:
            if line.startswith("Serial"):
                cpuserial = line[10:26]
                f.close()
                return cpuserial
        f.close()

        # try the cgroup file if running in docker
        f = open("/proc/self/cgroup", "r")
        line = f.readline()
        cpuserial = line.split("/docker/")[1][:16]
        f.close()
        return cpuserial
    except OSError:
        cpuserial = "ERROR000000000"

    return cpuserial


def get_system_data():
    """Return all the system data as a dictionary."""

    logger.debug("getting system data")
    system_data = {}
    system_data["uptime"] = get_uptime()
    system_data["current_time"] = datetime.datetime.now()
    system_data["load_avg"] = os.getloadavg()
    system_data["cpu_temp"] = get_cpu_temperature()

    return system_data


def get_system_memory():
    """Return the system memory as a dictionary."""

    logger.debug("getting system memory")
    system_mem = {}

    virtual_mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    system_mem["ram_used"] = virtual_mem.used // 2 ** 20  # MB
    system_mem["ram_total"] = virtual_mem.total // 2 ** 20  # MB
    system_mem["ram_free"] = virtual_mem.free // 2 ** 20  # MB
    system_mem["disk_used"] = round(float(disk.used) / 2 ** 30, 3)  # GB
    system_mem["disk_total"] = round(float(disk.total) / 2 ** 30, 3)  # GB
    system_mem["disk_free"] = round(float(disk.free) / 2 ** 30, 3)  # GB

    return system_mem


def get_storage():
    """Return the system storage as a dictionary."""

    logger.debug("getting device storage")
    disk = psutil.disk_usage("/")
    system_mem = {}
    system_mem["disk_used"] = round(float(disk.used) / 2 ** 30, 3)  # GB
    system_mem["disk_total"] = round(float(disk.total) / 2 ** 30, 3)  # GB
    system_mem["disk_free"] = round(float(disk.free) / 2 ** 30, 3)  # GB

    return system_mem
