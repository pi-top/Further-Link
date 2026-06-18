import getpass
import os
import tempfile
from unittest.mock import patch

import pytest
from mock import AsyncMock

from further_link.runner.py_process_handler import PyProcessHandler

user = getpass.getuser()


@pytest.mark.asyncio
async def test_venv_not_set():
    """No FURTHER_VENV -> uses system python3"""
    env_copy = os.environ.copy()
    env_copy.pop("FURTHER_VENV", None)

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, env_copy, clear=True):
            with patch("further_link.runner.py_process_handler.ProcessHandler._start") as mock_super_start:
                mock_super_start.return_value = None

                handler = PyProcessHandler(user=user)
                await handler._start(tmpdir, code="print('test')")

            # Check env param passed to super()._start
            mock_super_start.assert_called_once()
            call_kwargs = mock_super_start.call_args[1]
            assert call_kwargs.get("env", {}) == {}


@pytest.mark.asyncio
async def test_venv_set_valid():
    """FURTHER_VENV set + valid -> activates venv"""
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = os.path.join(tmpdir, "venv")
        bin_path = os.path.join(venv_path, "bin")
        os.makedirs(bin_path)

        # Create fake python3
        python_bin = os.path.join(bin_path, "python3")
        with open(python_bin, "w") as f:
            f.write("#!/bin/bash\n")

        code_dir = os.path.join(tmpdir, "code")
        os.makedirs(code_dir)

        env_copy = os.environ.copy()
        env_copy["FURTHER_VENV"] = venv_path

        with patch.dict(os.environ, env_copy, clear=True):
            with patch("further_link.runner.py_process_handler.ProcessHandler._start") as mock_super:
                mock_super.return_value = None

                handler = PyProcessHandler(user=user)
                await handler._start(code_dir, code="print('test')")

                mock_super.assert_called_once()
                call_kwargs = mock_super.call_args[1]
                env = call_kwargs.get("env", {})

                assert env.get("VIRTUAL_ENV") == venv_path
                assert f"{bin_path}:" in env.get("PATH", "")


@pytest.mark.asyncio
async def test_venv_set_invalid():
    """FURTHER_VENV set but invalid path -> ignores, uses system python"""
    env_copy = os.environ.copy()
    env_copy["FURTHER_VENV"] = "/nonexistent/venv"

    with tempfile.TemporaryDirectory() as tmpdir:
        with patch.dict(os.environ, env_copy, clear=True):
            with patch("further_link.runner.py_process_handler.ProcessHandler._start") as mock_super:
                mock_super.return_value = None

                handler = PyProcessHandler(user=user)
                await handler._start(tmpdir, code="print('test')")

            mock_super.assert_called_once()
            call_kwargs = mock_super.call_args[1]
            assert call_kwargs.get("env", {}) == {}


@pytest.mark.asyncio
async def test_venv_no_python_binary():
    """FURTHER_VENV points to dir without python3 -> ignores"""
    with tempfile.TemporaryDirectory() as tmpdir:
        venv_path = os.path.join(tmpdir, "venv")
        os.makedirs(os.path.join(venv_path, "bin"))
        # No python3 binary created

        code_dir = os.path.join(tmpdir, "code")
        os.makedirs(code_dir)

        env_copy = os.environ.copy()
        env_copy["FURTHER_VENV"] = venv_path

        with patch.dict(os.environ, env_copy, clear=True):
            with patch("further_link.runner.py_process_handler.ProcessHandler._start") as mock_super:
                mock_super.return_value = None

                handler = PyProcessHandler(user=user)
                await handler._start(code_dir, code="print('test')")

                mock_super.assert_called_once()
                call_kwargs = mock_super.call_args[1]
                assert call_kwargs.get("env", {}) == {}
