"""fd_device tools for starting up."""
import select
import socket

import requests
from sqlalchemy.orm.exc import NoResultFound

from fd_device.database.device import Connection
from fd_device.database.system import Interface
from fd_device.settings import get_config
from fd_device.system.info import get_ip_of_interface


def get_rabbitmq_address(logger, session):  # noqa: C901
    """Find and return the address of the RabbitMQ server to connect to."""

    config = get_config()
    presence_port = config.PRESENCE_PORT

    try:
        connection = session.query(Connection).one()
    except NoResultFound:
        connection = Connection()
        session.add(connection)

    # try previously found address (if available) to see if it is still working
    if connection.address:
        logger.debug(f"trying previous rabbitmq address of {connection.address}")
        if check_rabbitmq_address(logger, connection.address):
            logger.info("previously used rabbitmq address is still valid")
            return True

    # try to connect to dns name fm_rabbitmq. For example if farm_monitor and farm_device are on the same network
    try:
        address = socket.gethostbyname("fm_rabbitmq")
        if check_rabbitmq_address(logger, address):
            logger.info("'fm_rabbitmq' host was found and the url was valid")
            connection.address = address
            session.commit()
            return True

    except socket.gaierror:
        # name not known, so carry on to the next step
        logger.debug("'fm_rabbitmq' host was not found")

    # if all else fails, look for farm monitor presence notifier
    # get the first interface that is for farm monitor
    interface = session.query(Interface.interface).filter_by(is_for_fm=True).scalar()

    interface_address = get_ip_of_interface(interface, broadcast=True)
    logger.info("looking for FarmMonitor address on interface {}".format(interface))
    logger.debug("address is {}:{}".format(interface_address, presence_port))

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

    # Ask operating system to let us do broadcasts from socket
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    # Bind UDP socket to local port so we can receive pings
    sock.bind((interface_address, int(presence_port)))

    try:
        while True:
            timeout = 5
            ready = select.select([sock], [], [], timeout)

            # Someone answered our ping
            if ready[0]:
                _, addrinfo = sock.recvfrom(2)
                if check_rabbitmq_address(logger, addrinfo[0]):
                    sock.close()
                    logger.debug(
                        "Found FarmMonitor at {}:{}".format(addrinfo[0], addrinfo[1])
                    )
                    connection.address = addrinfo[0]
                    session.commit()
                    return True
                else:
                    logger.debug(
                        "Reply from {}:{}, but no rabbitmq server present".format(
                            addrinfo[0], addrinfo[1]
                        )
                    )

            else:
                logger.debug("No broadcast from FarmMonitor yet")

    except KeyboardInterrupt:
        sock.close()
        session.commit()
        return False


def check_rabbitmq_address(logger, address):
    """Check if the address is good, by trying to connect with the username and password."""

    url = "http://" + address + ":15672/api/aliveness-test/farm_monitor"

    config = get_config()
    user = config.RABBITMQ_USER
    password = config.RABBITMQ_PASSWORD

    logger.debug(f"testing connection to: {url} with auth {user} - {password}")

    try:
        r = requests.get(url, auth=(user, password))

        if r.status_code == requests.codes.ok:
            data = r.json()
            if data["status"] == "ok":
                logger.debug(f"the url: {url} was succesfull")
                return True
    except requests.exceptions.ConnectionError:
        logger.debug(f"the url: {url} had a connection failure")
        return False

    logger.debug(f"the url: {url} was unsuccesfull, or the auth failed.")
    return False
