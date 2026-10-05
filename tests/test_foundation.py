"""
C1 Foundation tests for package structure, metadata, and configuration.
"""

import finance_model_testbench
from finance_model_testbench.config import TestbenchConfig


def test_package_import_and_version():
    """Verify package imports correctly and exposes expected metadata."""
    assert hasattr(finance_model_testbench, "__version__")
    assert finance_model_testbench.__version__ == "0.1.0"


def test_default_config():
    """Verify default configuration initialization and immutability."""
    config = TestbenchConfig()
    assert config.environment == "development"
    assert config.allow_network is False
    assert config.strict_tolerance is True
    assert config.to_dict()["allow_network"] is False


def test_custom_config():
    """Verify custom configuration initialization."""
    config = TestbenchConfig(environment="test", allow_network=False, extra_options={"debug": True})
    assert config.environment == "test"
    assert config.extra_options == {"debug": True}
