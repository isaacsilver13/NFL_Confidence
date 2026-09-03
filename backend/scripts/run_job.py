"""Run one recurring NFL Confidence job manually."""

import argparse

from app.jobs.nfl_schedule import lock_expired_picks, run_current_week_sync, send_weekly_reminders


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "job",
        choices=("lock", "sync", "reminders"),
        help="Job to run: lock expired picks, sync scores, or send reminders.",
    )
    args = parser.parse_args()

    if args.job == "lock":
        result = lock_expired_picks()
        print(f"Locked {result} picks.")
    elif args.job == "sync":
        result = run_current_week_sync()
        print(f"Imported {result} games during the current-week sync.")
    else:
        result = send_weekly_reminders()
        print(f"Sent {result} weekly reminders.")


if __name__ == "__main__":
    main()
