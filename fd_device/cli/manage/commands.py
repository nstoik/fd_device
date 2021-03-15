"""CLI commands to manage the device."""
from datetime import datetime

import click
from alembic import command as al_command
from alembic.config import Config as AlConfig
from sqlalchemy.orm.exc import NoResultFound

from fd_device.database.base import get_session
from fd_device.database.device import Device, Grainbin
from fd_device.database.system import Hardware, Software, SystemSetup
from fd_device.device.temperature import get_connected_sensors
from fd_device.network.ethernet import get_interfaces
from fd_device.network.wifi import set_interfaces
from fd_device.settings import get_config
from fd_device.system.control import (
    set_device_name,
    set_hardware_info,
    set_sensor_info,
    set_software_info,
)


@click.command()
@click.option(
    "--standalone",
    is_flag=True,
    prompt="Standalone configuration?",
    default=True,
    help="Is standalone setup or not",
)
def first_setup(standalone):  # noqa: C901
    """First time setup. Load required data."""
    click.echo("first time setup")

    session = get_session()
    config = get_config()
    alembic_cnf = AlConfig(config.PROJECT_ROOT + "/alembic.ini")
    alembic_cnf.set_main_option("script_location", config.PROJECT_ROOT + "/migrations")

    try:
        system = session.query(SystemSetup).one()
    except NoResultFound:
        system = SystemSetup()
        session.add(system)

    if system.first_setup:
        click.echo("Setup has already been run")
        if not click.confirm("Do you want to run first time setup again?"):
            session.close()
            return

    system.standalone_configuration = standalone
    system.first_setup = True
    system.first_setup_time = datetime.now()

    session.commit()
    session.close()

    al_command.stamp(alembic_cnf, "head")

    if standalone:
        if click.confirm("Do you want to change the device name?"):
            name = click.prompt("Please enter a new device name")
            set_device_name(name)

    if click.confirm("Do you want to set hardware informations?"):
        hardware_version = click.prompt(
            "Enter the hardware version", default="pi3_0001"
        )
        gb_count = click.prompt(
            "Enter the number of grainbin reader chips on the board", default=0
        )
        set_hardware_info(hardware_version, gb_count)

    if click.confirm(
        "Do you want to set the internal and external sensor information?"
    ):
        current_sensors = get_connected_sensors(values=True)
        click.echo("Current sensor information: ")
        x = 1
        for sensor, temperature in current_sensors.items():
            click.echo(
                "{0}. Sensor: {1} Temperature: {2}".format(x, sensor, temperature)
            )
            x = x + 1

        interior_sensor = click.prompt(
            "Select which sensor is the internal temperature", default=1
        )
        exterior_sensor = click.prompt(
            "Select which sensor is the external temperature", default=2
        )
        set_sensor_info(interior_sensor, exterior_sensor)

    if click.confirm("Do you want to set the software information?"):
        software_version = click.prompt("Enter the software version")
        set_software_info(software_version)

    if standalone:
        if click.confirm("Do you want to set details for the interfaces?"):
            interfaces = get_interfaces()
            x = 1
            interface_details = []
            for interface in interfaces:
                click.echo("{0}. {1}".format(x, interface))
                x = x + 1
                interface_details.append(get_interface_details(interface))

            set_interfaces(interface_details)

    initialize_device()


def get_interface_details(interface):
    """Collect all required details for an interface from user.

    param: interface: a string that is the name of the interface

    Returns: a dictionary with required info. Keys are 'is_for_fm',
    'state', and 'ssid' and 'password' if applicable
    """
    info = {}
    info["name"] = interface
    info["is_for_fm"] = click.confirm(
        "Is this interface for Farm Monitor(y) or for external access(n)", default=False
    )
    info["state"] = click.prompt(
        "Should this interface be configured as an 'ap' or 'dhcp'", default="dhcp"
    )
    if info["state"] == "ap":
        creds = {}
        creds["ssid"] = click.prompt(
            "Enter the access point SSID", default="FarmMonitor"
        )
        creds["password"] = click.prompt(
            "Enter the access point password", default="raspberry"
        )
        info["creds"] = creds
    elif info["state"] == "dhcp":
        if click.confirm("Do you want to preopulate wifi credentials", default=True):
            creds = {}
            creds["ssid"] = click.prompt("Enter the wifi SSID", default="FarmMonitor")
            creds["password"] = click.prompt(
                "Enter the wifi password", default="raspberry"
            )
            info["creds"] = creds

    return info


def initialize_device():
    """Set up the Device info into the database.

    By this time, the Hardware and Software
    entries must be added to the database.
    """
    session = get_session()

    try:
        hd = session.query(Hardware).one()
        sd = session.query(Software).one()
    except NoResultFound:
        session.close()
        return

    try:
        device = session.query(Device).one()
    except NoResultFound:
        device = Device(
            id=hd.serial_number,
            interior_sensor=hd.interior_sensor,
            exterior_sensor=hd.exterior_sensor,
        )
        session.add(device)

    device.hardware_version = hd.hardware_version
    device.software_version = sd.software_version
    device.interior_sensor = hd.interior_sensor
    device.exterior_sensor = hd.exterior_sensor

    # set grainbin info
    grainbins = initialize_grainbin(device.id, hd.grainbin_reader_count)
    for grainbin in grainbins:
        session.merge(grainbin)
    device.grainbin_count = len(grainbins)

    session.commit()
    session.close()
    return


def initialize_grainbin(device_id, grainbin_reader_count):
    """Initalize grainbin info.

    param: device_id is the id of the device. Duh!
    param: grainbin_reader_count is how many 1W chips the device has
    """

    grainbins = []
    for bus_number in range(grainbin_reader_count):
        id = device_id + "." + str(bus_number).zfill(2)
        grainbin = Grainbin(id, bus_number, device_id)
        grainbins.append(grainbin)

    return grainbins
