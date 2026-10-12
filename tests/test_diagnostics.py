import json
import os
import subprocess
import sys


from diagnostics import cli, probes

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPECTED_KEYS = [key for key, _ in probes.PROBES]


def run(argv, capsys):
    code = cli.main(argv)
    return code, capsys.readouterr().out


def test_text_output_has_every_field(capsys):
    code, out = run([], capsys)
    assert code == 0
    for key in EXPECTED_KEYS:
        assert f"{key}: " in out
    assert "hostname" not in out


def test_json_output_matches_schema(capsys):
    code, out = run(["--json"], capsys)
    assert code == 0
    data = json.loads(out)
    assert list(data) == EXPECTED_KEYS
    assert data["timestamp_utc"].endswith("Z")


def test_hostname_only_with_flag(capsys):
    _, out = run(["--json"], capsys)
    assert "hostname" not in json.loads(out)
    _, out = run(["--json", "--include-hostname"], capsys)
    assert "hostname" in json.loads(out)


def test_failing_probe_reports_unknown(monkeypatch, capsys):
    def boom():
        raise OSError("probe failed")

    patched = [(k, boom if k == "cpu_model" else fn) for k, fn in probes.PROBES]
    monkeypatch.setattr(probes, "PROBES", patched)
    code, out = run(["--json"], capsys)
    assert code == 0
    data = json.loads(out)
    assert data["cpu_model"] == "unknown"
    assert data["os_name"] != "unknown"


def test_no_sensitive_values_leak(capsys):
    _, out = run(["--json"], capsys)
    home = os.path.expanduser("~")
    if home and home != "/":
        assert home not in out
    for var in ("USER", "LOGNAME"):
        val = os.environ.get(var)
        if val and len(val) > 3:
            assert val not in out


def test_module_entry_point():
    res = subprocess.run(
        [sys.executable, "-m", "diagnostics", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert res.returncode == 0, res.stderr
    assert list(json.loads(res.stdout)) == EXPECTED_KEYS
