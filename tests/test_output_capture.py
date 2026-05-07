"""Tests for cronwatcher.output_capture."""
import pytest

from cronwatcher.output_capture import (
    DEFAULT_MAX_BYTES,
    TRUNCATED_MARKER,
    CapturedOutput,
    capture_output,
)


# ---------------------------------------------------------------------------
# CapturedOutput helpers
# ---------------------------------------------------------------------------

def test_has_output_false_when_empty():
    co = CapturedOutput()
    assert not co.has_output()


def test_has_output_true_with_stdout():
    co = CapturedOutput(stdout="hello")
    assert co.has_output()


def test_has_errors_false_when_no_stderr():
    co = CapturedOutput(stdout="ok")
    assert not co.has_errors()


def test_has_errors_true_with_stderr():
    co = CapturedOutput(stderr="boom")
    assert co.has_errors()


# ---------------------------------------------------------------------------
# Roundtrip serialisation
# ---------------------------------------------------------------------------

def test_roundtrip():
    co = CapturedOutput(
        stdout="out", stderr="err",
        stdout_truncated=True, stderr_truncated=False,
    )
    assert CapturedOutput.from_dict(co.to_dict()) == co


def test_from_dict_defaults():
    co = CapturedOutput.from_dict({})
    assert co.stdout == ""
    assert co.stderr == ""
    assert co.stdout_truncated is False
    assert co.stderr_truncated is False


# ---------------------------------------------------------------------------
# capture_output — no truncation needed
# ---------------------------------------------------------------------------

def test_short_output_not_truncated():
    co = capture_output("hello", "world")
    assert co.stdout == "hello"
    assert co.stderr == "world"
    assert not co.stdout_truncated
    assert not co.stderr_truncated


def test_none_inputs_treated_as_empty():
    co = capture_output(None, None)
    assert co.stdout == ""
    assert co.stderr == ""


# ---------------------------------------------------------------------------
# capture_output — truncation
# ---------------------------------------------------------------------------

def test_stdout_truncated_when_over_limit():
    big = "x" * (DEFAULT_MAX_BYTES + 100)
    co = capture_output(big, "")
    assert co.stdout_truncated
    assert TRUNCATED_MARKER in co.stdout
    assert len(co.stdout.encode()) <= DEFAULT_MAX_BYTES + len(TRUNCATED_MARKER.encode()) + 4


def test_stderr_truncated_when_over_limit():
    big = "e" * (DEFAULT_MAX_BYTES + 1)
    co = capture_output("", big)
    assert co.stderr_truncated
    assert TRUNCATED_MARKER in co.stderr


def test_custom_max_bytes():
    co = capture_output("hello world", "", max_bytes=5)
    assert co.stdout_truncated
    assert co.stdout.startswith("hello")


def test_exact_limit_not_truncated():
    text = "a" * DEFAULT_MAX_BYTES
    co = capture_output(text, "")
    assert not co.stdout_truncated
    assert co.stdout == text
