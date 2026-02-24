#!/usr/bin/env python3
"""Simulate DataCatcher (X-Rite) keyboard injection for testing.

DataCatcher types a reading into the focused field then sends Tab.
This script replicates that sequence so you can test auto-advance and
highlight behaviour without needing Windows.

Usage:
    python datacatcher_sim.py [--weights N] [--delay SECONDS] [--startup SECONDS]

Examples:
    python datacatcher_sim.py                  # 1 weight, 0.4s between readings
    python datacatcher_sim.py --weights 3      # fill 3 weight tabs end-to-end
    python datacatcher_sim.py --delay 0.1      # fast run
    python datacatcher_sim.py --startup 5      # extra time to focus the app
"""

import argparse
import subprocess
import time

# Step labels matching STEP_LABELS_14 in core/models.py.
# The 100% step is locked to 100 in the app and skipped by Tab — omit it here.
STEP_LABELS = ["95", "90", "80", "70", "60", "50", "40", "30", "20", "10", "5", "3", "1"]
ROW_LABELS = ["D"] + STEP_LABELS  # 14 rows: density + 13 steps (100 is auto-filled)
COLOURS = ["C", "M", "Y", "K"]

# Realistic CMYK values, column-major (all C rows, then M, Y, K).
# No 100% step — that row is locked in the app.
READINGS = {
    "C": ["2.11", "0.95", "0.90", "0.80", "0.70", "0.60", "0.50",
          "0.40", "0.30", "0.20", "0.10", "0.05", "0.03", "0.01"],
    "M": ["1.80", "0.90", "0.85", "0.75", "0.65", "0.55", "0.45",
          "0.35", "0.27", "0.18", "0.09", "0.04", "0.02", "0.01"],
    "Y": ["1.66", "0.87", "0.82", "0.72", "0.62", "0.52", "0.42",
          "0.32", "0.24", "0.16", "0.08", "0.03", "0.02", "0.01"],
    "K": ["1.79", "0.93", "0.88", "0.78", "0.68", "0.58", "0.48",
          "0.38", "0.29", "0.19", "0.09", "0.04", "0.02", "0.01"],
}


def send_reading(value: str) -> None:
    """Type value into focused field then send Tab — exactly what DataCatcher does."""
    subprocess.run(["xdotool", "type", "--clearmodifiers", value], check=True)
    subprocess.run(["xdotool", "key", "Tab"], check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate DataCatcher keyboard injection")
    parser.add_argument(
        "--weights", type=int, default=1,
        help="Number of weight tabs to fill sequentially (default: 1)"
    )
    parser.add_argument(
        "--delay", type=float, default=0.4,
        help="Seconds between readings (default: 0.4)"
    )
    parser.add_argument(
        "--startup", type=int, default=3,
        help="Seconds to wait before starting — use this to focus the app (default: 3)"
    )
    args = parser.parse_args()

    print(f"Click the C-density field of the first weight tab, then wait.")
    for i in range(args.startup, 0, -1):
        print(f"  Starting in {i}...", end="\r", flush=True)
        time.sleep(1)
    print("  Sending readings now.   ")

    total = args.weights * len(COLOURS) * len(ROW_LABELS)
    sent = 0

    for weight in range(1, args.weights + 1):
        print(f"\nWeight {weight}/{args.weights}")
        for colour in COLOURS:
            for row_idx, row_label in enumerate(ROW_LABELS):
                value = READINGS[colour][row_idx]
                sent += 1
                print(f"  [{sent:3d}/{total}]  {colour}-{row_label:<4}  {value}")
                send_reading(value)
                if sent < total:
                    time.sleep(args.delay)

    print("\nDone.")


if __name__ == "__main__":
    main()
