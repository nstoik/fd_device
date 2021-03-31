"""fd_device tools for starting up."""
import select
import socket

import pika
from pika.exceptions import AMQPConnectionError
from sqlalchemy.orm.exc import NoResultFound

from fd_device.database.device import Connection
from fd_device.database.system import Interface
from fd_device.settings import get_config
from fd_device.system.info import get_ip_of_interface


def get_rabbitmq_address(logger, session):
    """Find and return the address of the RabbitMQ server to connect to."""

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

    possible_addresses = ["fm_rabbitmq", "host.docker.internal", "localhost"]

    for address in possible_addresses:
        logger.debug(f"testing address: {address}")
        try:
            address = socket.gethostbyname(address)
            if check_rabbitmq_address(logger, address):
                logger.info(f"'{address}' host was found and the url was valid")
                connection.address = address
                session.commit()
                return True

        except socket.gaierror:
            logger.debug(f"'{address}' host was not found")

    # if all else fails, look for farm monitor presence notifier
    return search_on_socket(logger, session, connection)


def search_on_socket(logger, session, connection):
    """Look for farm monitor presence notifier on the network."""

    config = get_config()
    presence_port = config.PRESENCE_PORT

    # get the first interface that is for farm monitor
    interface = session.query(Interface.interface).filter_by(is_for_fm=True).scalar()

    if interface is None:
        logger.warning(
            "Interface from database is None. Has initial configuration been run? Setting interface to 'eth0'"
        )
        interface = "eth0"

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
    """Check if the address is good, by trying to connect."""

    config = get_config()
    user = config.RABBITMQ_USER
    password = config.RABBITMQ_PASSWORD
    port = 5672
    virtual_host = config.RABBITMQ_VHOST

    credentials = pika.PlainCredentials(username=user, password=password)
    parameters = pika.ConnectionParameters(
        host=address, port=port, virtual_host=virtual_host, credentials=credentials
    )

    try:
        logger.debug(f"testing connection to: {address}")
        connection = pika.BlockingConnection(parameters=parameters)
        if connection.is_open:
            logger.debug(f"Connection to {address} is good.")
            connection.close()
            return True
    except AMQPConnectionError:
        logger.debug(f"Connection to {address} failed.")
        return False

    return False
