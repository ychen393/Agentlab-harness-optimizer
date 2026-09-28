"""Run the complete local AgentLab evidence story from one command."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.demo_evidence import build_demo_evidence, format_cli_report


def main() -> None:
    print(format_cli_report(build_demo_evidence()))


if __name__ == "__main__":
    main()
