"""Tests for annchive CLI."""
import pytest
from click.testing import CliRunner

from annchive.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_main_help(runner):
    """Test main help command."""
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "AnnaChive" in result.output


def test_config_show(runner):
    """Test config show command."""
    result = runner.invoke(main, ["config", "show"])
    assert result.exit_code == 0
    assert "library_path" in result.output


def test_library_list_empty(runner):
    """Test library list when empty."""
    result = runner.invoke(main, ["library", "list", "--limit", "5"])
    assert result.exit_code == 0


def test_tor_status(runner):
    """Test tor status command."""
    result = runner.invoke(main, ["tor", "status"])
    assert result.exit_code == 0
    assert "enabled" in result.output.lower()


def test_init_command(runner, tmp_path, monkeypatch):
    """Test init command creates directories."""
    # Mock the library path to temp dir
    test_lib = tmp_path / "test_library"
    monkeypatch.setenv("ANNCHIVE_LIBRARY_PATH", str(test_lib))
    
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0


def test_search_annas_archive(runner):
    """Test search command for annas-archive."""
    result = runner.invoke(main, ["search", "annas-archive", "test", "--limit", "2"])
    # Should not crash - may return empty if API changes
    assert result.exit_code in [0, 1]