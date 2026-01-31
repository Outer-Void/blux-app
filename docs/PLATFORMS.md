# Platforms

These notes are for contributors running tests or build tooling later. They do
not promise any specific UI framework or feature set.

## Termux (Android, native)
- Works well for lightweight checks, formatting, and quick scripts.
- Use the native toolchain when possible to avoid extra overhead.
- Some packages may be unavailable or slower to compile on-device.

## proot Debian (Android)
- Prefer this when you need Debian packages or more traditional build tooling.
- Expect higher CPU and disk overhead than native Termux.
- For reproducible builds, document package versions and toolchain choices in
  future project docs.
