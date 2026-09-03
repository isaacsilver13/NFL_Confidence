"""Tests for manual recurring-job command dispatch."""

import sys

import pytest

from scripts import run_job


@pytest.mark.parametrize(
    ("job_name", "function_name", "result", "expected_output"),
    (
        ("lock", "lock_expired_picks", 3, "Locked 3 picks."),
        ("sync", "run_current_week_sync", 5, "Imported 5 games during the current-week sync."),
        ("reminders", "send_weekly_reminders", 2, "Sent 2 weekly reminders."),
    ),
)
def test_main_dispatches_manual_job(
    monkeypatch, capsys, job_name, function_name, result, expected_output
):
    monkeypatch.setattr(sys, "argv", ["run_job", job_name])
    monkeypatch.setattr(run_job, function_name, lambda: result)

    run_job.main()

    assert capsys.readouterr().out.strip() == expected_output
