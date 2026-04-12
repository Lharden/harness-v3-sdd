"""conftest.py — Path resolution for Harness v3 tests."""
import os


def pytest_configure(config):
    """Set HARNESS_PLUGIN_ROOT if not already set."""
    if "HARNESS_PLUGIN_ROOT" not in os.environ:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.environ["HARNESS_PLUGIN_ROOT"] = root
