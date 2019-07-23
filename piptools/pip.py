from ._compat import InstallCommand


def get_pip_command():
    # Use pip's parser for pip.conf management and defaults.
    # General options (find_links, index_url, extra_index_url, trusted_host,
    # and pre) are defered to pip.
    # TODO get rid of get_pip_command
    return InstallCommand()


pip_command = get_pip_command()

# Get default values of the pip's options (including options from pip.conf).
pip_defaults = pip_command.parser.get_default_values()
