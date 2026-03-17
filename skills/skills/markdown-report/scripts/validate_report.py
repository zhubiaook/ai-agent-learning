#!/usr/bin/env python3
"""
validate_report.py
Checks that a Markdown report meets minimum structure requirements.
Usage: python scripts/validate_report.py <report.md>
Exit 0 = OK, exit 1 = validation errors.
"""
import sys
import os


def validate(path: str) -> int:
    if not path:
        print("Error: no file path provided")
        return 1
    if not os.path.exists(path):
        print(f"Error: file not found: {path}")
        return 1

    content = open(path, encoding="utf-8").read()
    errors = []

    if not content.strip().startswith("#"):
        errors.append("report must start with a # title")

    if "## Summary" not in content:
        errors.append("missing required '## Summary' section")

    if content.count("\n## ") < 1:
        errors.append("at least 2 ##-level sections required")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(validate(sys.argv[1] if len(sys.argv) > 1 else ""))
