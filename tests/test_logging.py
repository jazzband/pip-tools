from __future__ import annotations

from piptools.logging import LogContext


def test_indentation(runner):
    """
    Test LogContext.indentation() context manager increases indentation.
    """
    log = LogContext(indent_width=2)

    with runner.isolation() as streams:
        log.log("Test message 1")
        with log.indentation():
            log.log("Test message 2")
            with log.indentation():
                log.log("Test message 3")
            log.log("Test message 4")
        log.log("Test message 5")

        stderr_bytes = streams[1].getvalue()

    assert stderr_bytes.decode().splitlines() == [
        "Test message 1",
        "  Test message 2",
        "    Test message 3",
        "  Test message 4",
        "Test message 5",
    ]
