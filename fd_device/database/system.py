"""The system models for the database."""
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import SurrogatePK, reference_col


class SystemSetup(SurrogatePK):
    """The state of the setup of the system."""

    __tablename__ = "system_setup"

    first_setup = Column(Boolean, default=False)
    first_setup_time = Column(DateTime, default=func.now())
    standalone_configuration = Column(Boolean, default=True)

    def __init__(self):
        """Create the SystemSetup object."""
        return


class Wifi(SurrogatePK):
    """The wifi connections of the device."""

    __tablename__ = "system_wifi"

    name = Column(String(20), default="FarmMonitor")
    password = Column(String(20), default="raspberry")
    mode = Column(String(20), default="wpa")

    interface_id = reference_col("system_interface", nullable=True)
    interface = relationship("Interface", backref="credentials")

    def __init__(self):
        """Create the Wifi object."""
        return


class Interface(SurrogatePK):
    """The interface connections of the device."""

    __tablename__ = "system_interface"

    interface = Column(String(5), nullable=True)
    is_active = Column(Boolean, default=True)
    is_for_fm = Column(Boolean, default=False)
    is_external = Column(Boolean, default=False)
    state = Column(String(20))

    def __init__(self, interface):
        """Create the interface object."""

        self.interface = interface


class Hardware(SurrogatePK):
    """The hardware representation of the device."""

    __tablename__ = "system_hardware"

    device_name = Column(String(20))
    hardware_version = Column(String(20))

    interior_sensor = Column(String(20), nullable=True, default=None)
    exterior_sensor = Column(String(20), nullable=True, default=None)

    serial_number = Column(String(20))
    grainbin_reader_count = Column(Integer, default=0)

    def __init__(self):
        """Create the Hardware object."""
        return


class Software(SurrogatePK):
    """The software representation of the device."""

    __tablename__ = "system_software"

    software_version = Column(String(20))
    software_version_last = Column(String(20))

    def __init__(self):
        """Create the Software object."""
        return
