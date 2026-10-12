"""Tests for the diagnostics report: text, JSON, hostname flag, probe failure."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import diagnostics

ROOT = Path(__file__).resolve().parents[1]


def test_text_output_has_every_field(capsys):
    code = diagnostics.main([])
    captured = capsys.readouterr()
    assert code == 0
    lines = [line for line in captured.out.splitlines() if line]
    keys = [line.split(":", 1)[0] for line in lines]
    assert keys == list(diagnostics.FIELDS)
    assert "hostname" not in keys
    values = {line.split(":", 1)[0]: line.split(":", 1)[1].strip() for line in lines}
    for key in diagnostics.FIELDS:
        assert values[key] != ""
    # Timestamp is UTC ISO-8601 ending in Z.
    assert values["timestamp"].endswith("Z")
    assert "T" in values["timestamp"]


def test_json_output_matches_documented_schema(capsys):
    code = diagnostics.main(["--json"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert list(data.keys()) == list(diagnostics.FIELDS)
    assert "hostname" not in data
    assert data["version"] == diagnostics.__version__
    for key in diagnostics.FIELDS:
        assert data[key] not in (None, "")


def test_hostname_only_with_flag(capsys, monkeypatch):
    monkeypatch.setattr(diagnostics, "probe_hostname", lambda: "box.example")

    diagnostics.main([])
    plain = capsys.readouterr().out
    assert "hostname" not in plain
    assert "box.example" not in plain

    diagnostics.main(["--include-hostname"])
    with_host = capsys.readouterr().out
    assert "hostname: box.example" in with_host

    diagnostics.main(["--json", "--include-hostname"])
    data = json.loads(capsys.readouterr().out)
    assert data["hostname"] == "box.example"
    assert list(data.keys()) == list(diagnostics.FIELDS) + ["hostname"]


def test_probe_failure_is_unknown_and_exits_zero(capsys, monkeypatch):
    def boom():
        raise OSError("disk unavailable")

    monkeypatch.setattr(diagnostics, "probe_disk", boom)
    monkeypatch.setattr(diagnostics, "probe_cpu_model", lambda: (_ for _ in ()).throw(RuntimeError("cpu")))

    code = diagnostics.main([])
    captured = capsys.readouterr()
    assert code == 0
    values = {}
    for line in captured.out.splitlines():
        key, _, value = line.partition(":")
        values[key] = value.strip()
    assert values["disk_total"] == "unknown"
    assert values["disk_free"] == "unknown"
    assert values["cpu_model"] == "unknown"
    # A sibling probe still reports.
    assert values["version"] == diagnostics.__version__
    assert values["runtime"] != "unknown"


def test_json_probe_failure(capsys, monkeypatch):
    monkeypatch.setattr(
        diagnostics, "probe_memory", lambda: (_ for _ in ()).throw(OSError("mem"))
    )
    code = diagnostics.main(["--json"])
    assert code == 0
    data = json.loads(capsys.readouterr().out)
    assert data["memory_total"] == "unknown"
    assert data["memory_available"] == "unknown"
    assert data["os_name"] != "unknown"


def test_module_entry_point():
    result = subprocess.run(
        [sys.executable, "-m", "diagnostics", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    assert list(data.keys()) == list(diagnostics.FIELDS)
    assert "hostname" not in data
