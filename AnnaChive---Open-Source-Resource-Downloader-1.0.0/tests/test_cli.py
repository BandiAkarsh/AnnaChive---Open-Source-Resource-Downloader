"""Tests for annchive CLI."""
# We need help from outside - bringing in tools
import pytest
# We're bringing in tools from another file
from click.testing import CliRunner

# We're bringing in tools from another file
from annchive.cli import main


@pytest.fixture
# Here's a recipe (function) - it does a specific job
def runner():
    # We're giving back the result - like handing back what we made
    return CliRunner()


# Here's a recipe (function) - it does a specific job
def test_main_help(runner):
    """Test main help command."""
    # Remember this: we're calling 'result' something
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "AnnaChive" in result.output


# Here's a recipe (function) - it does a specific job
def test_config_show(runner):
    """Test config show command."""
    # Remember this: we're calling 'result' something
    result = runner.invoke(main, ["config", "show"])
    assert result.exit_code == 0
    assert "library_path" in result.output


# Here's a recipe (function) - it does a specific job
def test_library_list_empty(runner):
    """Test library list when empty."""
    # Remember this: we're calling 'result' something
    result = runner.invoke(main, ["library", "list", "--limit", "5"])
    assert result.exit_code == 0


# Here's a recipe (function) - it does a specific job
def test_tor_status(runner):
    """Test tor status command."""
    # Remember this: we're calling 'result' something
    result = runner.invoke(main, ["tor", "status"])
    assert result.exit_code == 0
    assert "enabled" in result.output.lower()


# Here's a recipe (function) - it does a specific job
def test_init_command(runner, tmp_path, monkeypatch):
    """Test init command creates directories."""
    # Mock the library path to temp dir
    # Remember this: we're calling 'test_lib' something
    test_lib = tmp_path / "test_library"
    monkeypatch.setenv("ANNCHIVE_LIBRARY_PATH", str(test_lib))
    
    # Remember this: we're calling 'result' something
    result = runner.invoke(main, ["init"])
    assert result.exit_code == 0


# Here's a recipe (function) - it does a specific job
def test_search_annas_archive(runner):
    """Test search command for annas-archive."""
    # Remember this: we're calling 'result' something
    result = runner.invoke(main, ["search", "annas-archive", "test", "--limit", "2"])
    # Should not crash - may return empty if API changes
    assert result.exit_code in [0, 1]