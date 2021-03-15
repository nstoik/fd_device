# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""
# pylint: disable=redefined-outer-name
import pytest
from _pytest.monkeypatch import MonkeyPatch

from fd_device.database.base import create_all_tables, drop_all_tables, get_session


@pytest.fixture(scope="session")
# pylint: disable=unused-argument
def monkeysession(request):
    """Create a MonkeyPatch object that can be scoped to a session.

    https://github.com/pytest-dev/pytest/issues/363#issuecomment-289830794
    """
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session", autouse=True)
def set_testing_env(monkeysession):
    """Set the environment variable for testing.

    This executes once for the entire session of testing.
    The environment variables are set back to the default after.
    """
    monkeysession.setenv("FD_DEVICE_CONFIG", "test")
    yield
    monkeysession.setenv("FD_DEVICE_CONFIG", "dev")


@pytest.fixture(scope="session")
def dbsession():
    """Returns an sqlalchemy session."""
    yield get_session()


@pytest.fixture()
def tables(dbsession):
    """Create all tables for testing. Delete when done."""
    create_all_tables()
    yield
    dbsession.close()
    drop_all_tables()
