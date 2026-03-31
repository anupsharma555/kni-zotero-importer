#!/usr/bin/env python3

"""GUI and CLI launcher for KNI Zotero Importer."""

from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

GUI_MODE_ARGS = {"--cli", "--stdin-file", "-h", "--help"}


def _needs_gui(argv: list[str]) -> bool:
    return "--cli" not in argv and "--stdin-file" not in argv and "-h" not in argv and "--help" not in argv


def _module_available(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _current_interpreter_satisfies(wants_gui: bool) -> bool:
    required = ["requests", "dotenv"]
    if wants_gui:
        required.extend(["tkinter", "_tkinter"])
    return all(_module_available(module_name) for module_name in required)


def _interpreter_satisfies(python_path: Path, wants_gui: bool) -> bool:
    probe = (
        "import importlib.util, sys\n"
        f"mods = {['requests', 'dotenv', 'tkinter', '_tkinter'] if wants_gui else ['requests', 'dotenv']}\n"
        "ok = all(importlib.util.find_spec(m) is not None for m in mods)\n"
        "raise SystemExit(0 if ok else 1)\n"
    )
    result = subprocess.run([str(python_path), "-c", probe], capture_output=True)
    return result.returncode == 0


def _prefer_project_venv() -> None:
    wants_gui = _needs_gui(sys.argv[1:])
    if _current_interpreter_satisfies(wants_gui):
        return
    project_root = Path(__file__).resolve().parent
    candidates = [
        Path("/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"),
        project_root / ".venv" / "bin" / "python3",
    ]
    current = Path(sys.executable).resolve()
    for candidate in candidates:
        if not candidate.exists():
            continue
        target = candidate.resolve()
        if target == current:
            continue
        if _interpreter_satisfies(target, wants_gui):
            os.execv(str(target), [str(target), str(project_root / "run_kni_zotero_importer.py"), *sys.argv[1:]])


_prefer_project_venv()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="KNI Zotero Importer")
    parser.add_argument("--stdin-file", default="", help="Read entries from a text file instead of the GUI")
    parser.add_argument("--cli", action="store_true", help="Read entries interactively from the terminal")
    parser.add_argument("--dry-run", action="store_true", help="Parse and resolve without writing to Zotero")
    parser.add_argument("--create-missing-collections", action="store_true", help="Create missing top-level Zotero collections when needed")
    return parser


def read_cli_input() -> str:
    print("Paste entries below. End input with a line containing only END.")
    lines: list[str] = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    return "\n".join(lines)


def main() -> int:
    args = build_parser().parse_args()
    if args.stdin_file:
        from src.importer import run_import_from_text_with_options

        text = Path(args.stdin_file).read_text(encoding="utf-8")
        report = run_import_from_text_with_options(
            text=text,
            dry_run=args.dry_run,
            create_missing_collections=args.create_missing_collections,
        )
        print(report.render_text())
        return 0 if not report.has_errors else 1
    if args.cli:
        from src.importer import run_import_from_text_with_options

        text = read_cli_input()
        report = run_import_from_text_with_options(
            text=text,
            dry_run=args.dry_run,
            create_missing_collections=args.create_missing_collections,
        )
        print(report.render_text())
        return 0 if not report.has_errors else 1
    from src.gui import launch_gui

    launch_gui()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
