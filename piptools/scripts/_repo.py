import optparse

import pip

from ..repositories import PyPIRepository


class PipCommand(pip.basecommand.Command):
    name = 'PipCommand'


def get_pip_options_and_pypi_repository(
        index_url=None, extra_index_url=None, no_index=None,
        find_links=None, cert=None, client_cert=None, pre=None,
        trusted_host=None):
    pip_command = get_pip_command()

    pip_args = []
    if find_links:
        for link in find_links:
            pip_args.extend(['-f', link])
    if index_url:
        pip_args.extend(['-i', index_url])
    if no_index:
        pip_args.extend(['--no-index'])
    if extra_index_url:
        for extra_index in extra_index_url:
            pip_args.extend(['--extra-index-url', extra_index])
    if cert:
        pip_args.extend(['--cert', cert])
    if client_cert:
        pip_args.extend(['--client-cert', client_cert])
    if pre:
        pip_args.extend(['--pre'])
    if trusted_host:
        for host in trusted_host:
            pip_args.extend(['--trusted-host', host])

    pip_options, _ = pip_command.parse_args(pip_args)

    session = pip_command._build_session(pip_options)
    repository = PyPIRepository(pip_options, session)
    return (pip_options, repository)


def get_pip_command():
    # Use pip's parser for pip.conf management and defaults.
    # General options (find_links, index_url, extra_index_url, trusted_host,
    # and pre) are defered to pip.
    pip_command = PipCommand()
    index_opts = pip.cmdoptions.make_option_group(
        pip.cmdoptions.index_group,
        pip_command.parser,
    )
    pip_command.parser.insert_option_group(0, index_opts)
    pip_command.parser.add_option(
        optparse.Option('--pre', action='store_true', default=False))

    return pip_command
