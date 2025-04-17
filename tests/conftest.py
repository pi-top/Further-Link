import os
from shutil import rmtree
from unittest.mock import MagicMock

import pytest
from mock import AsyncMock

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
    adapter.get_first.return_value = MagicMock()
    mocker.patch("further_link.util.bluetooth.server.Adapter", adapter)

    async def get_bus():
        return MagicMock()

    mocker.patch("further_link.util.bluetooth.server.get_message_bus", get_bus)


@pytest.fixture()
async def bluetooth_server():
    from further_link.util.bluetooth.dis_service import DeviceInformationService
    from further_link.util.bluetooth.uuids import DIS_SERVICE_UUID

    server = await create_bluetooth_app()

    # Explicitly add the DIS service if it's not already there
    if server.get_service(DIS_SERVICE_UUID) is None:
        dis_service = DeviceInformationService()
        server.services.append(dis_service)

    yield server
    server.stop()
