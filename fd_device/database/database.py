# -*- coding: utf-8 -*-
"""Database module, including the SQLAlchemy database object and DB-related utilities."""
from sqlalchemy import Column, ForeignKey, Integer

from fd_device.database.base import get_base

Base = get_base(with_query=True)


class CRUDMixin:
    """Mixin that adds convenience methods for CRUD (create, read, update, delete) operations."""

    @classmethod
    def create(cls, session, **kwargs):
        """Create a new record and save it the database."""
        instance = cls(**kwargs)
        return instance.save(session)

    def update(self, session, commit=True, **kwargs):
        """Update specific fields of a record."""
        for attr, value in kwargs.items():
            setattr(self, attr, value)
        return commit and self.save(session) or self

    def save(self, session, commit=True):
        """Save the record."""
        session.add(self)
        if commit:
            session.commit()
        return self

    def delete(self, session, commit=True):
        """Remove the record from the database."""
        session.delete(self)
        return commit and session.commit()


class Model(CRUDMixin, Base):  # type: ignore[valid-type, misc]
    """Base model class that includes CRUD convenience methods."""

    __abstract__ = True


# From Mike Bayer's "Building the app" talk
# https://speakerdeck.com/zzzeek/building-the-app
class SurrogatePK(object):
    """A mixin that adds a surrogate integer 'primary key' column named ``id`` to any declarative-mapped class."""

    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True)

    @classmethod
    def get_by_id(cls, record_id, session=None):
        """Get record by ID."""
        if any(
            (
                isinstance(record_id, (str, bytes)) and record_id.isdigit(),
                isinstance(record_id, (int, float)),
            ),
        ):
            if session:
                return session.query.get(int(record_id))
            else:
                return cls.query.get(int(record_id))
        return None


def reference_col(tablename, nullable=False, pk_name="id", **kwargs):
    """Column that adds primary key foreign key reference.

    Usage: ::

        category_id = reference_col('category')
        category = relationship('Category', backref='categories')
    """
    return Column(
        ForeignKey("{0}.{1}".format(tablename, pk_name)), nullable=nullable, **kwargs
    )
