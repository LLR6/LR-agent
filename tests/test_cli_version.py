from typer.testing import CliRunner

from lr_agent.__main__ import cli


runner = CliRunner()


def test_cli_version_flag():
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert result.stdout.startswith("lr-agent ")
