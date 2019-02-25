import sys

import mock
from click.testing import CliRunner

from piptools.scripts.sync import cli
from .utils import invoke


def test_run_as_module_sync():
    """piptools can be run as ``python -m piptools ...``."""

    status, output = invoke([
        sys.executable, '-m', 'piptools', 'sync', '--help',
    ])

    # Should have run pip-compile successfully.
    output = output.decode('utf-8')
    assert output.startswith('Usage:')
    assert 'Synchronize virtual environment with' in output
    assert status == 0


def test_quiet_option(tmpdir):
    """sync command can be run with `--quiet` or `-q` flag."""

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.txt', 'w') as req_in:
            req_in.write('six==1.10.0')

        with mock.patch('piptools.sync.check_call') as check_call:
            out = runner.invoke(cli, ['-q'])
            assert out.output == ''
            assert out.exit_code == 0
            # for every call to pip ensure the `-q` flag is set
            for call in check_call.call_args_list:
                assert '-q' in call[0][0]
