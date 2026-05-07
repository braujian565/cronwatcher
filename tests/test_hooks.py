"""Unit tests for cronwatcher.hooks."""
import sys
import pytest

from cronwatcher.hooks import (
    HookResult,
    _run_hook,
    run_pre_hooks,
    run_post_hooks,
    pre_hooks_passed,
)


# ---------------------------------------------------------------------------
# HookResult helpers
# ---------------------------------------------------------------------------

def test_hook_result_ok_when_zero():
    r = HookResult(hook_type="pre", command="echo hi",
                   returncode=0, stdout="hi", stderr="")
    assert r.ok is True


def test_hook_result_not_ok_when_nonzero():
    r = HookResult(hook_type="post", command="false",
                   returncode=1, stdout="", stderr="")
    assert r.ok is False


# ---------------------------------------------------------------------------
# _run_hook
# ---------------------------------------------------------------------------

def test_run_hook_success():
    r = _run_hook("pre", "echo hello")
    assert r.ok
    assert r.stdout == "hello"
    assert r.hook_type == "pre"


def test_run_hook_failure():
    r = _run_hook("post", "exit 42", timeout=5)
    assert not r.ok
    assert r.returncode == 42


def test_run_hook_timeout_returns_minus_one():
    r = _run_hook("pre", "sleep 10", timeout=1)
    assert r.returncode == -1
    assert "timeout" in r.stderr


# ---------------------------------------------------------------------------
# run_pre_hooks
# ---------------------------------------------------------------------------

def test_pre_hooks_all_pass():
    results = run_pre_hooks(["echo a", "echo b"])
    assert len(results) == 2
    assert all(r.ok for r in results)


def test_pre_hooks_stops_on_first_failure():
    results = run_pre_hooks(["exit 1", "echo should_not_run"])
    # Only the first hook should have been executed
    assert len(results) == 1
    assert not results[0].ok


def test_pre_hooks_empty_list():
    assert run_pre_hooks([]) == []


# ---------------------------------------------------------------------------
# run_post_hooks
# ---------------------------------------------------------------------------

def test_post_hooks_continues_after_failure():
    results = run_post_hooks(["exit 1", "echo still_runs"])
    assert len(results) == 2
    assert not results[0].ok
    assert results[1].ok


def test_post_hooks_empty_list():
    assert run_post_hooks([]) == []


# ---------------------------------------------------------------------------
# pre_hooks_passed
# ---------------------------------------------------------------------------

def test_pre_hooks_passed_true_when_all_ok():
    results = [
        HookResult("pre", "a", 0, "", ""),
        HookResult("pre", "b", 0, "", ""),
    ]
    assert pre_hooks_passed(results) is True


def test_pre_hooks_passed_false_when_any_fail():
    results = [
        HookResult("pre", "a", 0, "", ""),
        HookResult("pre", "b", 1, "", "err"),
    ]
    assert pre_hooks_passed(results) is False


def test_pre_hooks_passed_true_for_empty():
    assert pre_hooks_passed([]) is True
