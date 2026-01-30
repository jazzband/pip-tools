"""Tests for piptools._internal._pip_api.requirement_utils module."""

from __future__ import annotations

import pytest
from pip._internal.req import InstallRequirement
from pip._vendor.packaging.requirements import Requirement

from piptools._internal._pip_api.requirement_utils import (
    format_requirement,
    format_specifier,
    is_pinned_requirement,
    is_url_requirement,
    key_from_ireq,
    key_from_req,
    strip_extras,
)


class TestKeyFromIreq:
    """Tests for key_from_ireq function."""

    def test_simple_requirement(self, from_line):
        ireq = from_line("django==1.8")
        assert key_from_ireq(ireq) == "django"

    def test_normalized_name(self, from_line):
        ireq = from_line("Django==1.8")
        assert key_from_ireq(ireq) == "django"

    def test_with_extras(self, from_line):
        ireq = from_line("requests[security]==2.0")
        assert key_from_ireq(ireq) == "requests"


class TestKeyFromReq:
    """Tests for key_from_req function."""

    def test_simple_requirement(self):
        req = Requirement("django==1.8")
        assert key_from_req(req) == "django"

    def test_normalized_name(self):
        req = Requirement("Django_Project==1.0")
        assert key_from_req(req) == "django-project"


class TestIsUrlRequirement:
    """Tests for is_url_requirement function."""

    def test_not_url(self, from_line):
        ireq = from_line("django==1.8")
        assert is_url_requirement(ireq) is False

    def test_file_url(self, from_line):
        ireq = from_line("file:///path/to/package.zip")
        assert is_url_requirement(ireq) is True

    def test_https_url(self, from_line):
        ireq = from_line("https://example.com/package.zip")
        assert is_url_requirement(ireq) is True


class TestIsPinnedRequirement:
    """Tests for is_pinned_requirement function."""

    def test_pinned(self, from_line):
        ireq = from_line("django==1.8")
        assert is_pinned_requirement(ireq) is True

    def test_pinned_triple_equals(self, from_line):
        ireq = from_line("django===1.8")
        assert is_pinned_requirement(ireq) is True

    def test_not_pinned_greater(self, from_line):
        ireq = from_line("django>1.8")
        assert is_pinned_requirement(ireq) is False

    def test_not_pinned_compatible(self, from_line):
        ireq = from_line("django~=1.8")
        assert is_pinned_requirement(ireq) is False

    def test_not_pinned_wildcard(self, from_line):
        ireq = from_line("django==1.*")
        assert is_pinned_requirement(ireq) is False


class TestFormatRequirement:
    """Tests for format_requirement function."""

    def test_simple(self, from_line):
        ireq = from_line("django==1.8")
        assert format_requirement(ireq) == "django==1.8"

    def test_with_marker(self, from_line):
        from pip._vendor.packaging.markers import Marker

        ireq = from_line("django==1.8")
        marker = Marker('python_version >= "3.8"')
        result = format_requirement(ireq, marker=marker)
        assert result == 'django==1.8 ; python_version >= "3.8"'


class TestFormatSpecifier:
    """Tests for format_specifier function."""

    def test_single_specifier(self, from_line):
        ireq = from_line("django==1.8")
        assert format_specifier(ireq) == "==1.8"

    def test_multiple_specifiers(self, from_line):
        ireq = from_line("django>=1.8,<2.0")
        result = format_specifier(ireq)
        # Result should contain both specifiers (order may vary)
        assert ">=1.8" in result
        assert "<2.0" in result

    def test_no_specifier(self, from_line):
        ireq = from_line("django")
        assert format_specifier(ireq) == "any"


class TestStripExtras:
    """Tests for strip_extras function."""

    def test_no_extras(self):
        assert strip_extras("django") == "django"

    def test_single_extra(self):
        assert strip_extras("django[rest]") == "django"

    def test_multiple_extras(self):
        assert strip_extras("django[rest,security]") == "django"

    def test_nested_brackets(self):
        # This shouldn't happen in practice, but test behavior
        assert strip_extras("django[a][b]") == "django"
