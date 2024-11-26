# tests/test_cli/test_main.py
from click.testing import CliRunner
from looplm.cli.main import cli


def test_cli_help():
    """Test CLI help output"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "looplm - LLMs on the command line" in result.output


def test_cli_status_no_config():
    """Test status command with no configuration"""
    runner = CliRunner()
    result = runner.invoke(cli, ["--status"])
    assert result.exit_code == 0
    assert "Configuration Status" in result.output
