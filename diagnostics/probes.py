"""Individual system probes.

Each probe is isolated: if it raises, the report shows "unknown" for that
field instead of failing. Probes never read environment variables, user
names, home paths, or network details.
"""

import datetime
import os
import platform
import shutil
import subprocess
import sys

UNKNOWN = "unknown"


def _version():
    from . import __version__

    return __version__ or "dev"


def _os_name():
    return platform.system() or UNKNOWN


def _os_release():
    return platform.release() or UNKNOWN


def _kernel_version():
    return platform.version() or UNKNOWN


def _arch():
    return platform.machine() or UNKNOWN


def _runtime():
    return f"{platform.python_implementation()} {platform.python_version()}"


def _cpu_model():
    if sys.platform.startswith("linux"):
        with open("/proc/cpuinfo", encoding="utf-8") as fh:
            for line in fh:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    elif sys.platform == "darwin":
        # Fixed argv, no user input, no shell.
        out = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True, text=True, timeout=2, check=True,
        )
        return out.stdout.strip() or UNKNOWN
    return platform.processor() or UNKNOWN


def _cpu_count():
    return os.cpu_count() or UNKNOWN


def _meminfo():
    """Return (total_bytes, available_bytes)."""
    if sys.platform.startswith("linux"):
        vals = {}
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                key, rest = line.split(":", 1)
                if key in ("MemTotal", "MemAvailable"):
                    vals[key] = int(rest.split()[0]) * 1024
        return vals.get("MemTotal", UNKNOWN), vals.get("MemAvailable", UNKNOWN)
    if sys.platform == "darwin":
        out = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, timeout=2, check=True,
        )
        return int(out.stdout.strip()), UNKNOWN
    return UNKNOWN, UNKNOWN


def _mem_total():
    return _meminfo()[0]


def _mem_available():
    return _meminfo()[1]


def _disk_total():
    return shutil.disk_usage(os.getcwd()).total


def _disk_free():
    return shutil.disk_usage(os.getcwd()).free


def _timestamp():
    return (
        datetime.datetime.now(datetime.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _hostname():
    return platform.node() or UNKNOWN


# Ordered: this is the report schema. Keys are stable; see README.
PROBES = [
    ("version", _version),
    ("os_name", _os_name),
    ("os_release", _os_release),
    ("kernel_version", _kernel_version),
    ("arch", _arch),
    ("runtime", _runtime),
    ("cpu_model", _cpu_model),
    ("cpu_count", _cpu_count),
    ("memory_total_bytes", _mem_total),
    ("memory_available_bytes", _mem_available),
    ("disk_total_bytes", _disk_total),
    ("disk_free_bytes", _disk_free),
    ("timestamp_utc", _timestamp),
]

HOSTNAME_PROBE = ("hostname", _hostname)


def safe_call(fn):
    try:
        value = fn()
    except Exception:  # noqa: BLE001 - a probe must never break the report
        return UNKNOWN
    return UNKNOWN if value is None or value == "" else value


def collect(include_hostname=False):
    probes = list(PROBES)
    if include_hostname:
        probes.append(HOSTNAME_PROBE)
    return {key: safe_call(fn) for key, fn in probes}
