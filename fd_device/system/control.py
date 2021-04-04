"""Set information for the system."""
import logging
import subprocess

from sqlalchemy.orm.exc import NoResultFound

from fd_device.database.base import get_session
from fd_device.database.system import Hardware, Software
from fd_device.device.temperature import get_connected_sensors

from .info import get_device_name, get_serial

logger = logging.getLogger("fd.system.control")


def set_device_name(name):
    """Set the device name to the given name.

    TODO: change to hostnamectl command.
    """

    name = "hostname -b " + name
    subprocess.call(name)


def set_service_state(control):
    """Set the service state.

    TODO: implement this.
    """

    raise NotImplementedError


def set_sensor_info(interior, exterior):
    """Set the sensor details for the device.

    There should be two 1W sensors connected directly to the device.
    This gets the sensors and sets which one is interior and exterior into the Hardware table.
    input interior should be '1' or '2' and specifies which of the two sensors is the interior one.
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

    logger.debug(f"interior sensor is: {int_sensor}")
    logger.debug(f"exterior sensor is: {ext_sensor}")
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


def set_hardware_info(hardware_version: str, gb_reader_count: str):
    """Set the hardware info into the HardwareDefinition table.

    :param hardware_version: The hardware revision.
    :type hardware_version: str
    :param gb_reader_count: The number of 1Wire readerchips the FarmDevice has.
    :type gb_reader_count: str
    """

    logger.debug(
        f"setting version: {hardware_version} grainbin_reader: {gb_reader_count}"
    )
    session = get_session()

    device_name = get_device_name()
    serial_number = get_serial()

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


def set_software_info(software_version: str):
    """Set the software version info into the SoftwareDefinition table.

    :param software_version: The version of software
    :type software_version: str
    """

    logger.debug(f"setting software version: {software_version}")
    session = get_session()

    try:
        sd = session.query(Software).one()

    except NoResultFound:
        sd = Software()
        session.add(sd)

    sd.software_version = software_version

    session.commit()
    session.close()
