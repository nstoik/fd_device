"""Create a device update object."""
import datetime

from fd_device.database.base import get_session
from fd_device.database.device import Device
from fd_device.grainbin.update import get_grainbin_info


def get_device_info(session=None):
    """Return a device information dictionary."""

    close_session = False
    if not session:
        close_session = True
        session = get_session()

    device = session.query(Device).first()
    info = {}

    info["created_at"] = datetime.datetime.now()
    info["id"] = device.device_id
    info["hardware_version"] = device.hardware_version
    info["software_version"] = device.software_version

    info["grainbin_count"] = device.grainbin_count
    info["grainbin_data"] = get_grainbin_info(session)

    if close_session:
        session.close()

    return info
