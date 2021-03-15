from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Model, SurrogatePK, reference_col


class Connection(Model, SurrogatePK):
    __tablename__ = 'connection'
    address = Column(String(20))
    last_updated = Column(DateTime, onupdate=func.now())
    first_connected = Column(DateTime, default=func.now())
    is_connected = Column(Boolean, default=False)


class Grainbin(Model):
    __tablename__ = 'grainbin'
    id = Column(String(20), primary_key=True)
    bus_number = Column(Integer, nullable=False)
    creation_time = Column(DateTime, default=func.now())
    last_updated = Column(DateTime, onupdate=func.now())
    average_temp = Column(String(7))

    device_id = reference_col('device')

    def __init__(self, id, bus_number, device_id):
        self.id = id
        self.bus_number = bus_number
        self.device_id = device_id
        self.average_temp = 'unknown'

    def __repr__(self):
        return '<Grainbin: name={0.id!r}>'.format(self)


class Device(Model):
    __tablename__ = 'device'
    id = Column(String(20), primary_key=True)
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
    grainbins = relationship('Grainbin', backref='device')

    def __init__(self, id, interior_sensor='null',
                 exterior_sensor='null'):
        self.id = id
        self.interior_sensor = interior_sensor
        self.exterior_sensor = exterior_sensor

    def __repr__(self):
        return '<Device: id={0.id!r}>'.format(self)
