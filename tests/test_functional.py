"""Test functional aspects of the app."""

from fd_device.settings import TestConfig, get_config


def test_main_env():
    """Test that the main environment variable is set for testing."""

    config = get_config()
    assert config == TestConfig
