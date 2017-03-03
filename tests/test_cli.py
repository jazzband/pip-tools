import os
from textwrap import dedent
import subprocess

from click.testing import CliRunner

import pytest
from piptools.scripts.compile import cli


@pytest.yield_fixture
def pip_conf(tmpdir):
    test_conf = dedent("""\
        [global]
        index-url = http://example.com
        trusted-host = example.com
    """)

    pip_conf_file = 'pip.conf' if os.name != 'nt' else 'pip.ini'
    path = (tmpdir / pip_conf_file).strpath

    with open(path, 'w') as f:
        f.write(test_conf)

    old_value = os.environ.get('PIP_CONFIG_FILE')
    try:
        os.environ['PIP_CONFIG_FILE'] = path
        yield path
    finally:
        if old_value is not None:
            os.environ['PIP_CONFIG_FILE'] = old_value
        else:
            del os.environ['PIP_CONFIG_FILE']
        os.remove(path)


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


def test_find_links_option(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v', '-f', './libs1', '-f', './libs2'])

        # Check that find-links has been passed to pip
        assert 'Configuration:\n  -f ./libs1\n  -f ./libs2' in out.output


def test_extra_index_option(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v',
                                  '--extra-index-url', 'http://extraindex1.com',
                                  '--extra-index-url', 'http://extraindex2.com'])
        assert ('Using indexes:\n'
                '  http://example.com\n'
                '  http://extraindex1.com\n'
                '  http://extraindex2.com' in out.output)


def test_trusted_host(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v',
                                  '--trusted-host', 'example2.com'])
        print(out.output)
        assert ('--trusted-host example.com\n'
                '--trusted-host example2.com\n' in out.output)


def test_realistic_complex_sub_dependencies(tmpdir):

    # make a temporary wheel of a fake package
    subprocess.check_output(['pip', 'wheel',
                             '--no-deps',
                             '-w', str(tmpdir),
                             os.path.join('.', 'tests', 'fixtures', 'fake_package', '.')])

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.in', 'w') as req_in:
            req_in.write('fake_with_deps')  # require fake package

        out = runner.invoke(cli, ['-v',
                                  '-n', '--rebuild',
                                  '-f', str(tmpdir)])

        print(out.output)
        assert out.exit_code == 0
