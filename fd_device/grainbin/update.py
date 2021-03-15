"""Get update objects for the grainbins."""
from fd_device.database.base import get_session
from fd_device.database.device import Grainbin


def get_grainbin_info(session=None):
    """Get all grainbin information."""

    close_session = False

    if not session:
        close_session = True
        session = get_session()

    grainbins = session.query(Grainbin).all()
    print(grainbins)
    info = {}

    if close_session:
        session.close()

    return info
