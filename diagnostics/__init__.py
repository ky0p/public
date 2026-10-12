"""Local system-info report for bug reports.

Safe to paste into a public issue: no environment variables, usernames,
home paths, IP or MAC addresses, or network calls. Hostname is omitted
unless the caller passes include_hostname=True.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from typing import Callable

__version__ = "0.1.0"

UNKNOWN = "unknown"

# Stable JSON keys, in display order. Documented in the README.
FIELDS = (
    "version",
    "os_name",
    "os_release",
    "kernel",
    "arch",
    "runtime",
    "cpu_model",
    "cpu_count",
    "memory_total",
    "memory_available",
    "disk_total",
    "disk_free",
    "timestamp",
)

HOSTNAME_FIELD = "hostname"


def _safe(probe: Callable[[], object]) -> object:
    """Run one probe. Any failure becomes "unknown" and never raises."""
    try:
        value = probe()
    except Exception:
        return UNKNOWN
    if value is None or value == "":
        return UNKNOWN
    return value


def probe_version() -> str:
    return __version__ or "dev"


def probe_os_name() -> str:
    return platform.system()


def probe_os_release() -> str:
    return platform.release()


def probe_kernel() -> str:
    return platform.version()


def probe_arch() -> str:
    return platform.machine()


def probe_runtime() -> str:
    return f"{platform.python_implementation()} {platform.python_version()}"


def probe_cpu_count() -> int:
    count = os.cpu_count()
    if not count:
        raise OSError("cpu count unavailable")
    return count


def probe_cpu_model() -> str:
    system = platform.system()
    if system == "Linux":
        return _cpu_model_linux()
    if system == "Darwin":
        return _cpu_model_darwin()
    if system == "Windows":
        return platform.processor() or UNKNOWN
    return platform.processor() or UNKNOWN


def _cpu_model_linux() -> str:
    with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.lower().startswith("model name"):
                _, _, value = line.partition(":")
                name = value.strip()
                if name:
                    return name
    raise OSError("model name not in /proc/cpuinfo")


def _cpu_model_darwin() -> str:
    # Fixed argv only. Never interpolate user input into a shell command.
    out = subprocess.check_output(
        ["sysctl", "-n", "machdep.cpu.brand_string"],
        text=True,
        timeout=2,
    )
    return out.strip()


def probe_memory() -> tuple[object, object]:
    """Return (total, available) as byte counts, or unknown on failure."""
    system = platform.system()
    if system == "Linux":
        return _memory_linux()
    if system == "Darwin":
        return _memory_darwin()
    return UNKNOWN, UNKNOWN


def _memory_linux() -> tuple[int, int]:
    info: dict[str, int] = {}
    with open("/proc/meminfo", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            key, _, rest = line.partition(":")
            parts = rest.split()
            if not parts:
                continue
            # Values in /proc/meminfo are KiB.
            info[key] = int(parts[0]) * 1024
    total = info["MemTotal"]
    if "MemAvailable" in info:
        available = info["MemAvailable"]
    else:
        available = info["MemFree"] + info.get("Buffers", 0) + info.get("Cached", 0)
    return total, available


def _memory_darwin() -> tuple[int, int]:
    total = int(
        subprocess.check_output(
            ["sysctl", "-n", "hw.memsize"], text=True, timeout=2
        ).strip()
    )
    # page size * free pages. Fixed argv, no shell.
    page_size = int(
        subprocess.check_output(
            ["sysctl", "-n", "hw.pagesize"], text=True, timeout=2
        ).strip()
    )
    vm = subprocess.check_output(["vm_stat"], text=True, timeout=2)
    free_pages = 0
    for line in vm.splitlines():
        if line.startswith("Pages free:"):
            free_pages = int(line.split(":")[1].strip().rstrip("."))
            break
    else:
        raise OSError("Pages free not in vm_stat")
    return total, free_pages * page_size


def probe_disk(path: str | None = None) -> tuple[object, object]:
    """Total and free bytes for the filesystem holding path (default: cwd)."""
    usage = shutil.disk_usage(path or os.getcwd())
    return usage.total, usage.free


def probe_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def probe_hostname() -> str:
    return platform.node()


def collect(include_hostname: bool = False) -> dict[str, object]:
    """Collect every field. One probe failing never drops the others."""
    memory_total, memory_available = UNKNOWN, UNKNOWN
    try:
        memory_total, memory_available = probe_memory()
    except Exception:
        memory_total, memory_available = UNKNOWN, UNKNOWN

    disk_total, disk_free = UNKNOWN, UNKNOWN
    try:
        disk_total, disk_free = probe_disk()
    except Exception:
        disk_total, disk_free = UNKNOWN, UNKNOWN

    report: dict[str, object] = {
        "version": _safe(probe_version),
        "os_name": _safe(probe_os_name),
        "os_release": _safe(probe_os_release),
        "kernel": _safe(probe_kernel),
        "arch": _safe(probe_arch),
        "runtime": _safe(probe_runtime),
        "cpu_model": _safe(probe_cpu_model),
        "cpu_count": _safe(probe_cpu_count),
        "memory_total": memory_total if memory_total not in (None, "") else UNKNOWN,
        "memory_available": memory_available
        if memory_available not in (None, "")
        else UNKNOWN,
        "disk_total": disk_total if disk_total not in (None, "") else UNKNOWN,
        "disk_free": disk_free if disk_free not in (None, "") else UNKNOWN,
        "timestamp": _safe(probe_timestamp),
    }
    if include_hostname:
        report[HOSTNAME_FIELD] = _safe(probe_hostname)
    return report


def _keys(report: dict[str, object]) -> list[str]:
    keys: list[str] = [str(name) for name in FIELDS]
    if HOSTNAME_FIELD in report:
        keys.append(HOSTNAME_FIELD)
    return keys


def format_text(report: dict[str, object]) -> str:
    lines = [f"{key}: {report.get(key, UNKNOWN)}" for key in _keys(report)]
    return "\n".join(lines) + "\n"


def format_json(report: dict[str, object]) -> str:
    ordered = {key: report.get(key, UNKNOWN) for key in _keys(report)}
    return json.dumps(ordered, indent=2, sort_keys=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="diagnostics",
        description="Print a short system info report safe to paste into a bug report.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print one JSON object with stable keys instead of key: value lines.",
    )
    parser.add_argument(
        "--include-hostname",
        action="store_true",
        help="Include the machine hostname. Omitted by default.",
    )
    args = parser.parse_args(argv)
    # Collection must not be able to crash the report.
    try:
        report = collect(include_hostname=args.include_hostname)
    except Exception:
        report = {str(key): UNKNOWN for key in FIELDS}
        if args.include_hostname:
            report[HOSTNAME_FIELD] = UNKNOWN
    text = format_json(report) if args.as_json else format_text(report)
    sys.stdout.write(text)
    return 0
