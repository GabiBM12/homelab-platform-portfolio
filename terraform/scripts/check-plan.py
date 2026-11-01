"""Fail closed on deletion/replacement; no credentials are printed."""
import json
import sys


def check(plan):
    if any("delete" in item["change"]["actions"] for item in plan.get("resource_changes", [])):
        raise ValueError("Deletion/replacement refused; use a separately reviewed lifecycle procedure.")


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as source:
        try:
            check(json.load(source))
        except ValueError as error:
            sys.exit(str(error))
