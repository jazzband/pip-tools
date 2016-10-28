import os
from itertools import chain

from ._compat import ExitStack
from .click import unstyle
from .io import AtomicSaver
from .logging import log
from .utils import comment, format_requirement, key_from_req


def transitively(reverse_dependencies, ireq):
    dependencies = set()
    frontier = {key_from_req(ireq.req)}
    while frontier:
        next_req = frontier.pop()
        dependencies.add(next_req)
        frontier |= set(reverse_dependencies.get(next_req, [])) - dependencies

    return dependencies


class OutputWriter(object):
    def __init__(self, src_files, dst_files, dry_run, emit_header, emit_index,
                 annotate, default_index_url, index_urls, trusted_hosts,
                 format_control, phased, allow_unsafe=False):
        self.src_files = src_files
        self.dst_files = dst_files
        self.dry_run = dry_run
        self.emit_header = emit_header
        self.emit_index = emit_index
        self.annotate = annotate
        self.default_index_url = default_index_url
        self.index_urls = index_urls
        self.trusted_hosts = trusted_hosts
        self.format_control = format_control
        self.phased = phased
        self.allow_unsafe = allow_unsafe

    def _sort_key(self, ireq):
        return (not ireq.editable, str(ireq.req).lower())

    def write_header(self):
        if self.emit_header:
            yield comment('#')
            yield comment('# This file is autogenerated by pip-compile')
            yield comment('# To update, run:')
            yield comment('#')
            params = []
            if not self.emit_index:
                params += ['--no-index']
            if not self.annotate:
                params += ['--no-annotate']
            if self.phased:
                params += ['--phased']
            else:
                params += ['--output-file', self.dst_files[0]]
            params += self.src_files
            yield comment('#    pip-compile {}'.format(' '.join(params)))
            yield comment('#')

    def write_index_options(self):
        if self.emit_index:
            for index, index_url in enumerate(self.index_urls):
                if index_url.rstrip('/') == self.default_index_url:
                    continue
                flag = '--index-url' if index == 0 else '--extra-index-url'
                yield '{} {}'.format(flag, index_url)

    def write_trusted_hosts(self):
        for trusted_host in self.trusted_hosts:
            yield '--trusted-host {}'.format(trusted_host)

    def write_format_controls(self):
        for nb in self.format_control.no_binary:
            yield '--no-binary {}'.format(nb)
        for ob in self.format_control.only_binary:
            yield '--only-binary {}'.format(ob)

    def write_flags(self):
        emitted = False
        for line in chain(self.write_index_options(),
                          self.write_trusted_hosts(),
                          self.write_format_controls()):
            emitted = True
            yield line
        if emitted:
            yield ''

    def _iter_lines(self, from_srcs, results, reverse_dependencies, primary_packages):
        """
        A generator for requirements lines. The candidate set is all requirements in `results`.

        This candidate set is narrowed by only considering requirements that were
        transitively required by a requirement in `from_srcs`.
        """
        primary_packages = set(primary_packages)

        log.debug("For source files: {}".format(", ".join(from_srcs)))
        log.debug("  Primary packages:")
        for pkg in sorted(primary_packages):
            log.debug("    {}".format(pkg))

        log.debug("  Result packages:")
        for pkg in sorted(results, key=self._sort_key):
            log.debug("    {}".format(pkg))

        for line in self.write_header():
            yield line
        for line in self.write_flags():
            yield line

        UNSAFE_PACKAGES = {'setuptools', 'distribute', 'pip'}
        unsafe_packages = {r for r in results if r.name in UNSAFE_PACKAGES}
        packages = {r for r in results if r.name not in UNSAFE_PACKAGES}

        packages = sorted(packages, key=self._sort_key)
        unsafe_packages = sorted(unsafe_packages, key=self._sort_key)

        for ireq in packages:
            transitively_required_by = transitively(reverse_dependencies, ireq)
            if transitively_required_by & primary_packages:
                line = self._format_requirement(ireq, reverse_dependencies, primary_packages)
                yield line

        if unsafe_packages:
            yield ''
            yield comment('# The following packages are considered to be unsafe in a requirements file:')

            for ireq in unsafe_packages:
                line = self._format_requirement(
                    ireq, reverse_dependencies, primary_packages,
                    include_specifier=self.allow_unsafe)
                if self.allow_unsafe:
                    yield line
                else:
                    yield comment('# ' + line)

    def write(self, dst_file, from_srcs, results, reverse_dependencies, primary_packages):
        """
        Write out all requirements in `results` to the file `dst_file`, excluding
        those that were not derived from the input files `from_srcs`.

        `primary_packages` is the list of packages specifically defined in `from_srcs`.
        """
        with ExitStack() as stack:
            f = None
            if not self.dry_run:
                f = stack.enter_context(AtomicSaver(dst_file))

            for line in self._iter_lines(from_srcs, results, reverse_dependencies, primary_packages):
                log.info(line)
                if f:
                    f.write(unstyle(line).encode('utf-8'))
                    f.write(os.linesep.encode('utf-8'))

    def _format_requirement(self, ireq, reverse_dependencies, primary_packages, include_specifier=True):
        line = format_requirement(ireq, include_specifier=include_specifier)
        if not self.annotate or ireq.name in primary_packages:
            return line

        # Annotate what packages this package is required by
        required_by = set(reverse_dependencies.get(ireq.name.lower(), []))
        transitively_required_by = transitively(reverse_dependencies, ireq)
        if required_by and transitively_required_by & primary_packages:
            line = line.ljust(24)
            annotation = ', '.join(sorted(required_by))
            line += comment('  # via ' + annotation)
        return line
