#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch a detached process and write its PID.")
    parser.add_argument("--cwd", required=True, help="Working directory for the child process")
    parser.add_argument("--stdout", required=True, help="File path for stdout redirection")
    parser.add_argument("--stderr", help="File path for stderr redirection; defaults to stdout")
    parser.add_argument("--pid-file", required=True, help="Where to write the child PID")
    parser.add_argument("--env", action="append", default=[], help="Environment override in KEY=VALUE form")
    parser.add_argument("command", nargs=argparse.REMAINDER, help="Command to run after --")
    args = parser.parse_args()
    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        raise SystemExit("Missing command to launch")
    return args


def main() -> int:
    args = parse_args()
    env = os.environ.copy()
    for item in args.env:
        if "=" not in item:
            raise SystemExit(f"Invalid env override: {item!r}")
        key, value = item.split("=", 1)
        env[key] = value

    stdout_path = Path(args.stdout)
    stderr_path = Path(args.stderr) if args.stderr else stdout_path
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    if stderr_path != stdout_path:
        stderr_path.parent.mkdir(parents=True, exist_ok=True)

    with stdout_path.open("ab") as stdout_handle, stderr_path.open("ab") as stderr_handle:
        process = subprocess.Popen(
            args.command,
            cwd=args.cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
            close_fds=True,
        )

    Path(args.pid_file).write_text(f"{process.pid}\n", encoding="utf-8")
    print(process.pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
