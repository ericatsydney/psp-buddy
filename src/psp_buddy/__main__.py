import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="PSP Buddy protected battle tooling")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "validate", "run"):
        command = commands.add_parser(name, help=f"{name} (integration gates pending)")
        command.add_argument("--config", help="Path to local machine configuration")
    parser.parse_args()
    parser.error("live capabilities disabled until protected integration gates pass")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
