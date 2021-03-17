"""The device models for the database."""
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import SurrogatePK, reference_col


class Connection(SurrogatePK):
    """Represent the device's connecticon to the server."""

    __tablename__ = "connection"
    address = Column(String(20))
    last_updated = Column(DateTime, onupdate=func.now())
    first_connected = Column(DateTime, default=func.now())
    is_connected = Column(Boolean, default=False)


class Grainbin(SurrogatePK):
    """Represent a Grainbin that is connected to the device."""

    __tablename__ = "grainbin"
    name = Column(String(20), unique=True)
    bus_number = Column(Integer, nullable=False)
    creation_time = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    average_temp = Column(String(7))

    device_id = reference_col("device")

    def __init__(self, name, bus_number, device_id):
        """Create the Grainbin object."""
        self.name = name
        self.bus_number = bus_number
        self.device_id = device_id
        self.average_temp = "unknown"

    def __repr__(self):
        """Represent the grainbin in a useful format."""
        return f"<Grainbin name={self.name}"


class Device(SurrogatePK):
    """Represent the Device."""

    __tablename__ = "device"
    device_id = Column(String(20), unique=True)
    hardware_version = Column(String(20))
    software_version = Column(String(20))
    creation_time = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())

    interior_sensor = Column(String(20), nullable=True, default=None)
    exterior_sensor = Column(String(20), nullable=True, default=None)
    interior_temp = Column(String(7), nullable=True, default=None)
    exterior_temp = Column(String(7), nullable=True, default=None)

    # grainbin related data
    grainbin_count = Column(Integer, default=0)
    grainbins = relationship("Grainbin", backref="device")

    def __init__(self, device_id, interior_sensor="null", exterior_sensor="null"):
        """Create the Device object."""
        self.device_id = device_id
        self.interior_sensor = interior_sensor
        self.exterior_sensor = exterior_sensor

    def __repr__(self):
        """Represent the device in a useful format."""
        return f"<Device: device_id={self.device_id}>"
