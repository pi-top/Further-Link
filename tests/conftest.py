import os
from shutil import rmtree

import pytest
from mock import AsyncMock, MagicMock

os.environ["TESTING"] = "1"
from further_link.__main__ import create_bluetooth_app

from .dirs import PROJECTS_DIR, WORKING_DIRECTORY

os.environ["FURTHER_LINK_PORT"] = "8028"
os.environ["FURTHER_LINK_NOSSL"] = "true"
os.environ["FURTHER_LINK_WORK_DIR"] = WORKING_DIRECTORY
os.environ["FURTHER_LINK_MINISCREEN_PROJECTS_DIR"] = PROJECTS_DIR


@pytest.fixture(autouse=True)
def create_working_directory():
    os.makedirs(WORKING_DIRECTORY, exist_ok=True)
    yield
    rmtree(WORKING_DIRECTORY)


@pytest.fixture(autouse=True)
def clear_loggers():
    # this probably isn't the best solution to this problem
    # https://github.com/pytest-dev/pytest/issues/5502#issuecomment-647157873
    """Remove handlers from all loggers"""
    import logging

    loggers = [logging.getLogger()] + list(logging.Logger.manager.loggerDict.values())
    for logger in loggers:
        handlers = getattr(logger, "handlers", [])
        for handler in handlers:
            logger.removeHandler(handler)


@pytest.fixture(autouse=True)
def mock_bluez_peripheral(mocker):
    from .mocks.bluetooth.characteristic import characteristicMock
    from .mocks.bluetooth.service import ServiceMock

    # Mock the Service and characteristic for both regular service and DIS service
    mocker.patch("further_link.util.bluetooth.service.Service", ServiceMock)
    mocker.patch(
        "further_link.util.bluetooth.service.characteristic", characteristicMock
    )
    mocker.patch("further_link.util.bluetooth.dis_service.Service", ServiceMock)
    mocker.patch(
        "further_link.util.bluetooth.dis_service.characteristic", characteristicMock
    )

    mocker.patch("further_link.util.bluetooth.server.NoIoAgent", AsyncMock)
    mocker.patch("further_link.util.bluetooth.server.Advertisement", AsyncMock)

    adapter = AsyncMock()
    adapter_instance = AsyncMock()
    adapter.get_first = AsyncMock(return_value=adapter_instance)

    # Create a proxy object that's not an AsyncMock
    proxy = MagicMock()
    proxy.get_interface = lambda *args: adapter_props

    # Attach the proxy directly without lambda
    adapter_instance._proxy = proxy

    mocker.patch("further_link.util.bluetooth.server.Adapter", adapter)

    # Create a class to handle the interface methods
    class AdapterPropsInterface:
        async def call_set(self, *args, **kwargs):
            return None

        async def call_register_application(self, *args, **kwargs):
            return None

    adapter_props = AdapterPropsInterface()

    adapter_obj = AsyncMock()
    adapter_obj.get_interface = lambda *args: adapter_props

    # Create a class to handle bus operations
    class MockBus:
        def __init__(self):
            self.exported = {}

        def export(self, path, interface):
            self.exported[path] = interface
            return None

        def get_proxy_object(self, *args):
            return adapter_obj

        def disconnect(self, *args, **kwargs):
            return None

    bus = MockBus()

    async def get_bus():
        return bus

    mocker.patch("further_link.util.bluetooth.server.get_message_bus", get_bus)


@pytest.fixture()
async def bluetooth_server():
    server = await create_bluetooth_app()
    yield server
    server.stop()
