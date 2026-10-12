import argparse
import json

from .probes import collect


def _human_bytes(value):
    if not isinstance(value, int):
        return str(value)
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return str(value)


def format_text(report):
    lines = []
    for key, value in report.items():
        shown = _human_bytes(value) if key.endswith("_bytes") else value
        lines.append(f"{key}: {shown}")
    return "\n".join(lines)


def format_json(report):
    return json.dumps(report, indent=2)


def build_parser():
    parser = argparse.ArgumentParser(
        prog="diagnostics",
        description="Print system info that is safe to paste into a bug report.",
    )
    parser.add_argument("--json", action="store_true", help="output JSON")
    parser.add_argument(
        "--include-hostname",
        action="store_true",
        help="include the machine hostname (omitted by default)",
    )
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    report = collect(include_hostname=args.include_hostname)
    print(format_json(report) if args.json else format_text(report))
    return 0
