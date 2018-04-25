class PipToolsError(Exception):
    pass


class NoCandidateFound(PipToolsError):
    def __init__(self, ireq, candidates_tried, index_urls):
        self.ireq = ireq
        self.candidates_tried = candidates_tried
        self.index_urls = index_urls

    def __str__(self):
        sorted_candidates = sorted(self.candidates_tried)
        versions = []
        pre_versions = []

        for candidate in sorted(self.candidates_tried):
            version = str(candidate.version)
            if candidate.version.is_prerelease:
                pre_versions.append(version)
            else:
                versions.append(version)

        lines = [
            'Could not find a version that matches {}'.format(self.ireq),
        ]

        if versions:
            lines.append('Tried: {}'.format(', '.join(versions)))

        if pre_versions:
            lines.append('Skipped pre-versions: {}'.format(', '.join(pre_versions)))

        if versions or pre_versions:
            lines.append('There are incompatible versions in the resolved dependencies.')
        else:
            lines.append('No versions found')
            lines.append('{} {} reachable?'.format(
                'Were' if len(self.index_urls) > 1 else 'Was', ' or '.join(self.index_urls))
            )
        return '\n'.join(lines)


class UnsupportedConstraint(PipToolsError):
    def __init__(self, message, constraint):
        super(UnsupportedConstraint, self).__init__(message)
        self.constraint = constraint

    def __str__(self):
        message = super(UnsupportedConstraint, self).__str__()
        return '{} (constraint was: {})'.format(message, str(self.constraint))


class IncompatibleRequirements(PipToolsError):
    def __init__(self, ireq_a, ireq_b):
        self.ireq_a = ireq_a
        self.ireq_b = ireq_b

    def __str__(self):
        message = "Incompatible requirements found: {} and {}"
        return message.format(self.ireq_a, self.ireq_b)
