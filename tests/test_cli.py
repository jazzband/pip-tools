import os
import sys

import pytest
import pip

from click.testing import CliRunner
from piptools.scripts.compile import cli



@pytest.fixture
def pip_conf(request):
    """
    inject a fake pip.{ini,conf} inside current env
    """
    test_conf = """
[global]
index-url = http://example.com
trusted-host = example.com
    """
    #write pip.conf (pip.ini) at root of virtualenv
    pip_conf_file = 'pip.conf' if os.name != 'nt' else 'pip.ini'
    pip_conf_file = os.path.join(sys.prefix, pip_conf_file)
    real_pip_conf = None
    if os.path.exists(pip_conf_file):
        # backup real file
        with open(pip_conf_file) as original:
            real_pip_conf = original.read()

    with open(pip_conf_file, 'w') as pip_conf:
        pip_conf.write(test_conf)
    
    def tear_down():
        if real_pip_conf:
            with open(pip_conf_file, 'w') as pip_conf:
                pip_conf.write(real_pip_conf)
        else:
            os.remove(pip_conf_file)

    request.addfinalizer(tear_down)
    
    return pip_conf_file


@pytest.fixture
def wheel(tmpdir):
    """
    creates a temporary wheel with one depenendency: pip-tools==1.1.5
    """
    pip.main(['wheel', '-b', tmpdir.strpath, '--no-deps', '-w', tmpdir.strpath, os.path.abspath('tests/fixtures/fake_project')]) 

    return tmpdir.join('sample-1.2.3-py2.py3-none-any.whl').strpath
    


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


def test_can_compile_requirements_from_wheel(wheel):

    runner = CliRunner()

    with runner.isolated_filesystem():
        out = runner.invoke(cli, [wheel])

    # massage output
    output = ' '.join(out.output.split())
    assert 'pip-tools==1.1.5 # via sample sample==1.2.3' in output
