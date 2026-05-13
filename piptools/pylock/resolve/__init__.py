"""Run pip's resolver across many target environments without the NxM cost.

Pip's resolver works against a single point environment, so covering several
platforms and python versions naively takes one full resolution per cell.
This package collapses cells that share a dep graph into cohorts, resolves
each cohort once, and replicates the result to every env in the cohort,
so the lock pipeline can scale env coverage without scaling resolutions.
"""

from __future__ import annotations

from ._orchestrate import resolve

__all__ = [
    "resolve",
]
