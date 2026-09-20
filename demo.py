"""Run the complete local AgentLab evidence story from one command."""

from app.demo_evidence import build_demo_evidence, format_cli_report


def main() -> None:
    print(format_cli_report(build_demo_evidence()))


if __name__ == "__main__":
    main()
