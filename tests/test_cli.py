import os
import sys

import pytest

from click.testing import CliRunner
from piptools.scripts.compile import cli

@pytest.fixture
def pip_conf(request):
    test_conf = """
[global]
index-url = http://example.com
trusted-host = example.com
    """
    #write pip.conf (pip.ini) at root of virtualenv
    pip_conf_file = 'pip.conf' if os.name != 'nt' else 'pip.ini'
    pip_conf_file = os.path.join(sys.prefix, pip_conf_file)
    with open(pip_conf_file, 'w') as pip_conf:
        pip_conf.write(test_conf)
    
    def tear_down():
        os.remove(pip_conf_file)

    request.addfinalizer(tear_down)
    
    return pip_conf_file


def test_default_pip_conf_read(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        # preconditions
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v'])

        # check that we have our index-url as specified in pip.conf
        assert 'Using indexes:\n  http://example.com' in out.output
        assert '--index-url http://example.com' in out.output


def test_command_line_overrides_pip_conf(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        # preconditions
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v', '-i', 'http://override.com'])

        # check that we have our index-url as specified in pip.conf
        assert 'Using indexes:\n  http://override.com' in out.output
