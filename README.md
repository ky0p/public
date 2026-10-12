This is a test project.

## Reporting a bug

Please include a diagnostics report with your bug report:

```sh
python -m diagnostics          # human-readable
python -m diagnostics --json   # machine-readable
```

The report is designed to be safe to paste publicly: it contains no
environment variables, usernames, home paths, IP/MAC addresses, or
credentials. The hostname is omitted unless you pass `--include-hostname`.
Any field that cannot be read is reported as `unknown`.

JSON keys (stable): `version`, `os_name`, `os_release`, `kernel_version`,
`arch`, `runtime`, `cpu_model`, `cpu_count`, `memory_total_bytes`,
`memory_available_bytes`, `disk_total_bytes`, `disk_free_bytes`,
`timestamp_utc`, and `hostname` (only with `--include-hostname`).

## Development

```sh
pip install pytest
python -m pytest
```

Requires Python 3.8+; standard library only at runtime.
