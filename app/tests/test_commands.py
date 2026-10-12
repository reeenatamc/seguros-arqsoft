"""Every management command has to at least import."""

import importlib
import pkgutil

import pytest

import app.management.commands as commands_pkg

COMMANDS = [m.name for m in pkgutil.iter_modules(commands_pkg.__path__)]


@pytest.mark.parametrize("name", COMMANDS)
def test_command_module_imports(name):
    module = importlib.import_module(f"app.management.commands.{name}")
    assert hasattr(module, "Command")
