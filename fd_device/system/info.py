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


def get_uptime() -> str:
    """Get the system uptime.

    :return: The uptime of the system
    :rtype: str
    """

    logger.debug("getting uptime")
    uptime = subprocess.check_output(["uptime", "-p"], universal_newlines=True)
    return str(uptime[3:])


def get_uptime_seconds() -> int:
    """Get the system uptime in seconds.

    :return: The uptime of the system in seconds.
    :rtype: int
    """

    logger.debug("getting uptime in seconds")
    uptime = subprocess.check_output(["cat", "/proc/uptime"], universal_newlines=True)

    seconds = int(float(uptime.split()[0]))
    return seconds


def get_cpu_temperature() -> float:
    """Get the CPU temperature.

    :return: The CPU temperature of the device.
    :rtype: float
    """

    logger.debug("getting CPU temperature")
    try:
        filepath = "/sys/class/thermal/thermal_zone0/temp"
        res = subprocess.check_output(["cat", filepath], universal_newlines=True)
        return float(int(res) / 1000)

    except subprocess.CalledProcessError:
        logger.warning("Unable to retrieve CPU temperature. Returning -99.9")
        return -99.9


def get_service_status() -> bool:
    """Get the status of the service.

    :raises NotImplementedError: TODO: need to implement
    :return: True if the service is active, otherwise False
    :rtype: bool
    """
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


def get_device_name() -> str:
    """Get the name of the device.

    :return: The name of the device
    :rtype: str
    """

    logger.debug("getting device name")
    device_name = socket.gethostname()
    return device_name


def get_serial() -> str:
    """Get the serial numbr of the device.

    TODO: make serial number consistent even if docker container changes.

    :return: The serial number of the device. The length will be 16 characters
    :rtype: str
    """

    logger.debug("getting serial number")
    # Extract serial
    cpuserial = "0000000000000000"
    try:
        # first try cpuinfo file
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("Serial"):
                    cpuserial = line[10:26]
                    return cpuserial

        # try the cgroup file if running in docker
        with open("/proc/self/cgroup", "r") as f:
            for line in f:
                if "/docker/" in line:
                    cpuserial = line.split("/docker/")[1][:16]
                    return cpuserial
    except OSError:
        cpuserial = "ERROR000000000"

    return cpuserial


def get_system_data() -> dict:
    """Get all the system data.

    :return: The system data with the following keys: 'uptime', 'current_time', load_avg', and 'cpu_temp'
    :rtype: dict
    """

    logger.debug("getting system data")
    system_data = {}
    system_data["uptime"] = get_uptime()
    system_data["current_time"] = str(datetime.datetime.now())
    system_data["load_avg"] = str(os.getloadavg())
    system_data["cpu_temp"] = str(get_cpu_temperature())

    return system_data


def get_system_memory() -> dict:
    """Get the system memory.

    :return: The system memory with the following keys: 'ram_used', ram_total', 'ram_free',
    'disk_used', 'disk_total', and 'disk_free'
    :rtype: dict
    """

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


def get_storage() -> dict:
    """Get the system storage.

    :return: The system storage with the following keys: 'disk_used', 'disk_total', and 'disk_free'
    :rtype: dict
    """

    logger.debug("getting device storage")
    disk = psutil.disk_usage("/")
    system_mem = {}
    system_mem["disk_used"] = round(float(disk.used) / 2 ** 30, 3)  # GB
    system_mem["disk_total"] = round(float(disk.total) / 2 ** 30, 3)  # GB
    system_mem["disk_free"] = round(float(disk.free) / 2 ** 30, 3)  # GB

    return system_mem
