"""Get update objects for the grainbins."""
import datetime as dt

from sqlalchemy.orm.session import Session

from fd_device.database.base import get_session
from fd_device.database.device import Grainbin


def get_grainbin_info(session: Session = None) -> dict:
    """Get all grainbin information.

    Args:
        session (Session, optional): The database session. Defaults to None.

    Returns:
        dict: All the grainbin information.
    """

    close_session = False

    if not session:
        close_session = True
        session = get_session()

    grainbins = session.query(Grainbin).all()
    print(grainbins)
    info = {}

    info["created_at"] = dt.datetime.now()

    if close_session:
        session.close()

    return info
