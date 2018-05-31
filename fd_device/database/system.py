from sqlalchemy import Column, Boolean, DateTime, String, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .database import Model, SurrogatePK, reference_col


class SystemSetup(Model, SurrogatePK):
    __tablename__ = 'system_setup'

    first_setup = Column(Boolean, default=False)
    first_setup_time = Column(DateTime, default=func.now())
    standalone_configuration = Column(Boolean, default=True)

    def __init__(self):
        return


class Wifi(Model, SurrogatePK):
    __tablename__ = 'system_wifi'

    wifi_name = Column(String(20), default="FarmMonitor")
    wifi_password = Column(String(20), default="raspberry")
    wifi_mode = Column(String(20), default="wpa")

    interface = reference_col('system_interface', pk_name='interface')

    def __init__(self):
        return


class Interface(Model):
    __tablename__ = 'system_interface'

    interface = Column(String(5), primary_key=True)
    is_active = Column(Boolean, default=True)
    is_for_fm = Column(Boolean, default=False)
    is_external = Column(Boolean, default=False)
    state = Column(String(20))

    credentials = relationship("Wifi")

    def __init__(self, interface):

        self.interface = interface
        return


class Hardware(Model, SurrogatePK):
    __tablename__ = 'system_hardware'

    device_name = Column(String(20))
    hardware_version = Column(String(20))

    interior_sensor = Column(String(20), nullable=True, default=None)
    exterior_sensor = Column(String(20), nullable=True, default=None)

    serial_number = Column(String(20))
    grainbin_reader_count = Column(Integer, default=0)

    def __init__(self):
        return


class Software(Model, SurrogatePK):
    __tablename__ = 'system_software'

    software_version = Column(String(20))

    def __init__(self):
        return