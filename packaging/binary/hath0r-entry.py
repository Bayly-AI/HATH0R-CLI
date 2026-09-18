"""PyInstaller entrypoint for the standalone hath0r binary."""

from __future__ import annotations

from hath0r_cli.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
