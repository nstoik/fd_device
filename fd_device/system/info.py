import subprocess
import datetime
import os
import psutil
import logging
import netifaces
import socket

logger = logging.getLogger('fd.system.info')


def get_ip_of_interface(interface, broadcast=False):

    if not broadcast:
        ip = netifaces.ifaddresses(interface)[2][0]['addr']

    else:
        ip = netifaces.ifaddresses(interface)[2][0]['broadcast']

    return ip


def get_uptime():
    logger.debug("getting uptime")
    uptime = subprocess.check_output(["uptime", "-p"], universal_newlines=True)
    return str(uptime[3:])


def get_uptime_seconds():

    logger.debug("getting uptime in seconds")
    uptime = subprocess.check_output(["cat", "/proc/uptime"], universal_newlines=True)

    seconds = int(float(uptime.split()[0]))
    return seconds


def getCPUtemperature():

    logger.debug("getting CPU temperature")
    filepath = "/sys/class/thermal/thermal_zone0/temp"
    res = subprocess.check_output(["cat", filepath], universal_newlines=True)
    return float(int(res) / 1000)


def get_service_status():

    raise NotImplementedError

    logger.debug("getting service status")
    command = ['sudo', 'systemctl', 'is-active', 'farm-monitor.service']
    status = ""
    try:
        status = subprocess.check_output(command, universal_newlines=True)
    except subprocess.CalledProcessError:
        pass

    if status.startswith('active'):
        return True
    else:
        return False


def get_device_name():

    logger.debug("getting device name")
    device_name = socket.gethostname()
    return device_name


def getserial():

    logger.debug("getting serial number")
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = "ERROR000000000"

    return cpuserial


def get_system_data():

    logger.debug("getting system data")
    system_data = {}
    system_data['uptime'] = get_uptime()
    system_data['current_time'] = datetime.datetime.now()
    system_data['load_avg'] = os.getloadavg()
    system_data['cpu_temp'] = getCPUtemperature()

    return system_data


def get_system_memory():

    logger.debug("getting system memory")
    system_mem = {}

    virtual_mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    system_mem['ram_used'] = virtual_mem.used // 2**20  # MB
    system_mem['ram_total'] = virtual_mem.total // 2**20  # MB
    system_mem['ram_free'] = virtual_mem.free // 2**20  # MB
    system_mem['disk_used'] = round(float(disk.used) / 2**30, 3)  # GB
    system_mem['disk_total'] = round(float(disk.total) / 2**30, 3)  # GB
    system_mem['disk_free'] = round(float(disk.free) / 2**30, 3)  # GB

    return system_mem


def get_storage():

    logger.debug("getting device storage")
    disk = psutil.disk_usage('/')
    system_mem = {}
    system_mem['disk_used'] = round(float(disk.used) / 2**30, 3)  # GB
    system_mem['disk_total'] = round(float(disk.total) / 2**30, 3)  # GB
    system_mem['disk_free'] = round(float(disk.free) / 2**30, 3)  # GB

    return system_mem
