This is a test project.

## Reporting a bug

Paste a diagnostics report into the issue so we know the environment. It is local only (no network calls) and omits hostnames, usernames, home paths, and network addresses.

```
python -m diagnostics
```

Add `--json` for one JSON object. Add `--include-hostname` only if a maintainer asks for the hostname.

### JSON keys

`python -m diagnostics --json` prints these keys, in this order:

| Key | Meaning |
| --- | --- |
| version | Package version, or `dev` if unset |
| os_name | OS name (`Linux`, `Darwin`, `Windows`, ...) |
| os_release | OS release |
| kernel | Kernel version string |
| arch | Machine architecture |
| runtime | Language implementation and version, e.g. `CPython 3.13.1` |
| cpu_model | CPU model, or `unknown` |
| cpu_count | Logical CPU count |
| memory_total | Total memory in bytes, or `unknown` |
| memory_available | Available memory in bytes, or `unknown` |
| disk_total | Total bytes on the filesystem holding the current directory |
| disk_free | Free bytes on that filesystem |
| timestamp | UTC time, ISO 8601, `YYYY-MM-DDTHH:MM:SSZ` |
| hostname | Only present with `--include-hostname` |

A field that cannot be read is the string `unknown`. The command still exits 0.
