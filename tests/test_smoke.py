"""Smoke tests: the package imports, exposes a version, and the CLI runs."""
import tarseem
from tarseem.cli import main


def test_version_present():
    assert isinstance(tarseem.__version__, str) and tarseem.__version__


def test_cli_stub_returns_zero():
    assert main(["doctor"]) == 0
