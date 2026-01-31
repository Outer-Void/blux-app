# Platforms

These notes are for contributors running tests or build tooling later. They do
not promise any specific UI framework or feature set.

## Termux (Android, native)
- Works well for lightweight checks, formatting, and quick scripts.
- Use the native toolchain when possible to avoid extra overhead.
- Some packages may be unavailable or slower to compile on-device.

Typical setup:

```bash
pkg update
pkg install python git
```

Run the read-only viewer:

```bash
python blux_view.py --input-dir /path/to/output
```

## proot Debian (Android)
- Prefer this when you need Debian packages or more traditional build tooling.
- Expect higher CPU and disk overhead than native Termux.
- For reproducible builds, document package versions and toolchain choices in
  future project docs.

Typical setup:

```bash
apt update
apt install -y python3 git
```

Run the read-only viewer:

```bash
python3 blux_view.py --input-dir /path/to/output
```
