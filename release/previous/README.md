# Previous Releases & Binary Archives

This directory stores archived, previous releases of the **Hath0r CLI** standalone binaries, Python distributions, and fileset packages.

---

## 🏛️ Directory Structure & Retention Policy

When a new version of the Hath0r CLI is built and released:
1. Any previous active release binaries and packages are rotated into a dedicated version subdirectory:
   ```text
   release/previous/
   ├── <version>/                     # e.g., 0.2.0/ or 0.3.0/
   │   ├── hath0r-darwin-arm64
   │   ├── hath0r-darwin-x86_64
   │   ├── hath0r-linux-arm64
   │   ├── hath0r-linux-x86_64
   │   ├── hath0r-windows-x64.cmd
   │   ├── hath0r_cli-<version>-py3-none-any.whl
   │   ├── hath0r_cli-<version>.tar.gz
   │   ├── hath0r-fileset-<version>.tar.gz
   │   └── CHECKSUMS.sha256
   └── README.md
   ```
2. Each archived version folder contains its own self-contained, immutable `CHECKSUMS.sha256` verification file.
3. The latest active release is always hosted in the root `release/` directory of both `HATH0R-CLI` and `hath0r-framework`.

---

## 🔒 Verification

To verify the integrity of any previous binary:
```bash
cd release/previous/<version>
shasum -a 256 -c CHECKSUMS.sha256
```
