import logging
import subprocess

from sqlalchemy.orm.exc import NoResultFound

from fd_device.database.base import get_session
from fd_device.database.system import Hardware, Software
from fd_device.device.temperature import get_connected_sensors

from .info import get_device_name, getserial

logger = logging.getLogger('fd.system.control')


def set_device_name(name):

    name = "hostname -b "+ name
    subprocess.call(name)
    return

def set_service_state(control):

    raise NotImplementedError


def set_sensor_info(interior, exterior):
    """
    there should be two 1W sensors connected directly to the device.
    This gets the sensors and sets which one is interior and exterior
    into the Hardware table.
    input interior should be '1' or '2' and specifies which of the two sensors
    is the interior one.
    """

    logger.debug("setting sensor info for device")
    interior = int(interior)
    exterior = int(exterior)
    # get the 1W sensors that are connected directly to the device
    # theses are the interior and exterior temp sensors
    sensors = get_connected_sensors()

    int_sensor = "no_sensor_selected"
    ext_sensor = "no_sensor_selected"

    try:
        int_sensor = sensors[interior]
    except ValueError:
        pass
    try:
        ext_sensor = sensors[exterior]
    except ValueError:
        pass

    logger.debug("interior sensor is: {0}".format(int_sensor))
    logger.debug("exterior sensor is: {0}".format(ext_sensor))
    # now set the sensor info into the tables
    session = get_session()
    try:
        hd = session.query(Hardware).one()

    except NoResultFound:
        hd = Hardware()
        session.add(hd)

    hd.interior_sensor = int_sensor
    hd.exterior_sensor = ext_sensor

    session.commit()
    session.close()

    return


def set_hardware_info(hardware_version, gb_reader_count):
    """
    Set the hardware info into the HardwareDefinition table.
    hardware_version is a string representing what revison of hardware
    wifi_chip is the chip of the wifi adapter
    gb_reader_count is the number of 1Wire readerchips the FarmDevice has
    """

    logger.debug("setting version: {0} grainbin_reader: {1}".format(hardware_version,
                                                                    gb_reader_count))
    session = get_session()

    device_name = get_device_name()
    serial_number = getserial()

    try:
        hd = session.query(Hardware).one()

    except NoResultFound:
        hd = Hardware()
        session.add(hd)

    hd.hardware_version = hardware_version
    hd.device_name = device_name
    hd.serial_number = serial_number
    hd.grainbin_reader_count = int(gb_reader_count)

    session.commit()
    session.close()

    return


def set_software_info(software_version):
    """
    Set the software version info into the SoftwareDefinition table.
    software_version is a string representing what revison of software
    """
    logger.debug("setting software version: {0}".format(software_version))
    session = get_session()

    try:
        sd = session.query(Software).one()

    except NoResultFound:
        sd = Software()
        session.add(sd)

    sd.software_version = software_version

    session.commit()
    session.close()

    return
