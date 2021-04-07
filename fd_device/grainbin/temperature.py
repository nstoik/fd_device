"""Module to interface with the temperature sensors using the 1wire protocol."""
from glob import glob
from typing import List


def all_busses() -> List:
    """Get all busses connected to the device.

    Returns:
        List: A list of paths for all bussess connected.
    """
    return glob("/mnt/1wire/bus.*")


def get_bus_path(bus_number: str) -> str:
    """Get the file path for a specific bus.

    Args:
        bus_number (str): The bus number to get the path for.

    Returns:
        str: The file path for that bus number.
    """
    return "/mnt/1wire/bus." + bus_number


def all_sensors(bus_path: str = None, family: str = "28") -> List:
    """Get all sensors connected to a specific bus.

    Args:
        bus_path (str, optional): The file path of the bus to read. Defaults to None.
        family (str, optional): The family of the sensor to read. Defaults to '28'.

    Returns:
        List: A list of sensor paths for a specific bus.
    """

    if not bus_path:
        return []
    path = bus_path + "/" + family + ".*"
    return glob(path)


def read_sensor(  # noqa: C901  pylint: disable=too-many-arguments
    sensor_path: str,
    file: str = "temperature10",
    read_id: bool = True,
    read_temphigh: bool = True,
    read_templow: bool = True,
    read_temperature: bool = True,
) -> dict:
    """Read the data from a sensor and return it as a dict.

    Args:
        sensor_path (str): The file path to the sensor to read.
        file (str, optional): The file to read. Defaults to 'temperature10'.
        read_id (bool, optional): Whether or not to read the ID of the sensor. Defaults to True.
        read_temphigh (bool, optional): Whether or not to read the temphigh of the sensor. Defaults to True.
        read_templow (bool, optional): Whether or not to read the templow of the sensor. Defaults to True.
        read_temperature (bool, optional): Whether or not to read the temperature of the sensor. Defaults to True.

    Returns:
        dict: A dictionary of the data read from the sensor.
              A key is present for every read_* argument that is True.
              The value is 'None' if there is an error reading the sensor.
    """
    data = {}

    # id
    if read_id:
        try:
            id_file = sensor_path + "/id"
            with open(id_file) as f:
                data["id"] = f.readline()
        except IOError:
            data["id"] = "None"

    # cable number
    if read_temphigh:
        try:
            temph_file = sensor_path + "/temphigh"
            with open(temph_file) as f:
                data["temphigh"] = f.readline()
        except IOError:
            data["temphigh"] = "None"

    # sensor number
    if read_templow:
        try:
            templ_file = sensor_path + "/templow"
            with open(templ_file) as f:
                data["templow"] = f.readline()
        except IOError:
            data["templow"] = "None"

    # temperature
    if read_temperature:
        try:
            temperature_file = sensor_path + "/" + file
            with open(temperature_file) as f:
                data["temperature"] = f.readline()
        except IOError:
            data["temperature"] = "None"

    return data
