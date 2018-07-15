import socket
import select
import requests
from sqlalchemy.orm.exc import NoResultFound

from fd_device.database.system import SystemSetup, Interface
from fd_device.database.device import Connection
from fd_device.system.info import get_ip_of_interface
from fd_device.settings import get_config

def get_rabbitmq_address(logger, session):

    config = get_config()
    presence_port = config.PRESENCE_PORT

    try:
        connection = session.query(Connection).one()
    except NoResultFound:
        connection = Connection()
        session.add(connection)

    # check if device configuration is standalone
    if not session.query(SystemSetup.standalone_configuration).scalar():
        logger.debug("Combined installation detected. Rabbitmq address is 127.0.0.1")
        connection.address = '127.0.0.1'
        if check_rabbitmq_address(connection.address):
            session.commit()
            return True
        else:
            logger.error("Rabbitmq address check of 127.0.0.1 failed. Maybe check credentials")
            return False

    # try previously found address (if available) to see if it is still working
    if connection.address:
        if check_rabbitmq_address(connection.address):
            return True

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
                if check_rabbitmq_address(addrinfo[0]):
                    sock.close()
                    logger.debug("Found FarmMonitor at {}:{}".format(addrinfo[0], addrinfo[1]))
                    connection.address = addrinfo[0]
                    session.commit()
                    return True
                else:
                    logger.debug("Reply from {}:{}, but no rabbitmq server present".format(addrinfo[0], addrinfo[1]))

            else:
                logger.debug("No broadcast from FarmMonitor yet")

    except KeyboardInterrupt:
        sock.close()
        session.commit()
        return False


def check_rabbitmq_address(address):

    url = 'http://' + address + ':15672/api/aliveness-test/farm_monitor'

    config = get_config()
    user = config.RABBITMQ_USER
    password = config.RABBITMQ_PASSWORD

    r = requests.get(url, auth=(user, password))

    if r.status_code == requests.codes.ok:
        data = r.json()
        if data['status'] == 'ok':
            return True
    return False
