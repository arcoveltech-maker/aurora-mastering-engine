"""Pytest fixtures for Aurora backend tests."""
import pytest


@pytest.fixture
def app():
    from app.main import app as fastapi_app
    return fastapi_app
