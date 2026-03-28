"""E2E test configuration."""
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: mark test as end-to-end")
