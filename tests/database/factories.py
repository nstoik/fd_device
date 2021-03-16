"""Database factories to help in tests."""
# pylint: disable=too-few-public-methods,no-self-argument,unused-argument
from factory import Sequence, post_generation
from factory.alchemy import SQLAlchemyModelFactory
from sqlalchemy.orm import Session

from fd_device.database.device import Device, Grainbin


class BaseFactory(SQLAlchemyModelFactory):
    """Base factory."""

    @classmethod
    def create(cls, session, **kwargs):
        """Override the create method of the SQLALchemyModelFactory class.

        Adds the variable session so that the sqlalchemy_session can be
        passed in and overwritten. The sqlalchemy_session is passed in this
        way so that the new object can be properly saved in the correct session.
        """
        cls._meta.sqlalchemy_session = session
        return super().create(**kwargs)

    class Meta:
        """Factory configuration."""

        abstract = True
        sqlalchemy_session = None


class DeviceFactory(BaseFactory):
    """Device Factory."""

    device_id = Sequence(lambda n: f"Test Device{n}")

    class Meta:
        """Factory configuration."""

        model = Device


class GrainbinFactory(BaseFactory):
    """Grainbin factory."""

    device_id = "set in custom_grainbin_save"
    name = Sequence(lambda n: f"Test Grainbin{n}")
    bus_number = Sequence(int)

    @post_generation
    def custom_grainbin_save(obj, create, extracted, **kwargs):  # noqa: N805
        """Custom function to add proper device.id to grainbin.

        I tried doing this with SubFactory, but I could not get it
        to work with also passing in a custom session object ;).
        """
        if not create:
            return
        session = Session.object_session(obj)
        device = DeviceFactory.create(session)
        device.save(session)
        obj.device_id = device.id
        return

    class Meta:
        """Factory Configuration."""

        model = Grainbin
