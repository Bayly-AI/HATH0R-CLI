# Hath0r CLI Standalone Executable & Package Releases

This directory contains pre-compiled, zero-dependency standalone binaries, Python packages, and fileset archives of the **Hath0r CLI Operator** (`hath0r`).

The Hath0r CLI is the single, definitive tool required to initialize, govern, audit, and orchestrate autonomous AI multi-agent workflows across any repository or codebase.

---

## 📦 Available Release Artifacts (Latest Version)

### Standalone Executable Binaries (Zero Dependencies)

| Platform | Architecture | Binary File |
| :--- | :--- | :--- |
| **macOS** | Apple Silicon (`arm64`) | [`release/hath0r-darwin-arm64`](hath0r-darwin-arm64) |
| **macOS** | Intel (`x86_64`) | [`release/hath0r-darwin-x86_64`](hath0r-darwin-x86_64) |
| **Linux** | ARM64 (`aarch64`) | [`release/hath0r-linux-arm64`](hath0r-linux-arm64) |
| **Linux** | x86_64 (`amd64`) | [`release/hath0r-linux-x86_64`](hath0r-linux-x86_64) |
| **Windows**| x64 | [`release/hath0r-windows-x64.cmd`](hath0r-windows-x64.cmd) |

### Python Package & Fileset Distributions

| Distribution | Type | File Pattern |
| :--- | :--- | :--- |
| **Python Wheel** | Pip Wheel (`.whl`) | [`release/hath0r_cli-*.whl`](.) |
| **Source Tarball** | Source (`.tar.gz`) | [`release/hath0r_cli-*.tar.gz`](.) |
| **Hath0r Fileset** | Member Template Archive | [`release/hath0r-fileset-*.tar.gz`](.) |

---

## 🏛️ Previous Release Archives

Archived previous releases and older standalone binaries are preserved under the [`release/previous/`](previous/) directory.

---

## 🚀 Quick Start (Zero Setup Required)

### 1. Verify and Make Executable (macOS / Linux)
```bash
chmod +x release/hath0r-darwin-arm64   # macOS Apple Silicon
# or
chmod +x release/hath0r-linux-x86_64   # Linux x86_64
```

### 2. Verify Health & Environment
```bash
./release/hath0r-darwin-arm64 doctor
```

### 3. Initialize Any Repository with Hath0r
```bash
cd /path/to/target-project
/path/to/HATH0R-CLI/release/hath0r-darwin-arm64 init
```

---

## 🔒 Verification & Checksums

Integrity checksums for all binary and package artifacts in this directory are recorded in [`release/CHECKSUMS.sha256`](CHECKSUMS.sha256).

Verify with:
```bash
shasum -a 256 -c release/CHECKSUMS.sha256
```
