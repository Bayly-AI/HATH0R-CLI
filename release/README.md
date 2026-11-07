# Hath0r CLI Standalone Executable & Package Releases

This directory contains pre-compiled, zero-dependency standalone binaries, Python packages, and fileset archives of the **Hath0r CLI Operator** (`hath0r`).

The Hath0r CLI is the single, definitive tool required to initialize, govern, audit, and orchestrate autonomous AI multi-agent workflows across any repository or codebase.

---

## 📦 Available Release Artifacts (Latest Version)

### Standalone Executable Binaries (Zero Dependencies)

Pre-compiled standalone binaries for all supported platforms are published as verifiable assets on [GitHub Releases](https://github.com/Bayly-AI/HATH0R-CLI/releases).

| Platform | Architecture | Release Asset |
| :--- | :--- | :--- |
| **macOS** | Apple Silicon (`arm64`) | [hath0r-<ver>-darwin-arm64](https://github.com/Bayly-AI/HATH0R-CLI/releases/latest) |
| **macOS** | Intel (`x86_64`) | [hath0r-<ver>-darwin-x64](https://github.com/Bayly-AI/HATH0R-CLI/releases/latest) |
| **Linux** | ARM64 (`aarch64`) | [hath0r-<ver>-linux-arm64](https://github.com/Bayly-AI/HATH0R-CLI/releases/latest) |
| **Linux** | x86_64 (`amd64`) | [hath0r-<ver>-linux-x64](https://github.com/Bayly-AI/HATH0R-CLI/releases/latest) |
| **Windows**| x64 | [hath0r-<ver>-windows-x64.zip](https://github.com/Bayly-AI/HATH0R-CLI/releases/latest) |

### Platform Release Folders (`release/{mac,windows,vscode}`)

| Folder / Artifact | Type | Path |
| :--- | :--- | :--- |
| **`release/mac/`** | **Mac Release Folder** (DMG Installer, macOS Binaries, Fileset, Wizard Scripts) | [`release/mac/`](mac/) |
| **macOS Install Wizard (`.dmg`)** | macOS Disk Image (`Hath0r Install Wizard.app`) | [`release/mac/Hath0r-Install-Wizard.dmg`](mac/Hath0r-Install-Wizard.dmg) |
| **`release/windows/`** | **Windows Release Folder** (EXE Installer, Windows CLI Wrapper, Fileset, Wizard Scripts) | [`release/windows/`](windows/) |
| **Windows Install Wizard (`.exe`)** | Windows x64 Standalone Launcher | [`release/windows/Hath0r-Install-Wizard.exe`](windows/Hath0r-Install-Wizard.exe) |
| **`release/vscode/`** | **VSCode Extension Release Folder** (`.vsix` Marketplace Package & Staged Extension) | [`release/vscode/`](vscode/) |
| **VSCode Extension (`.vsix`)** | Visual Studio Code Control Plane Extension | [`release/vscode/hath0r-vscode.vsix`](vscode/hath0r-vscode.vsix) |
| **`release/previous/`** | **Previous Releases Archive** (`release/previous/<version>/{mac,windows,vscode}`) | [`release/previous/`](previous/) |

---

## 🏛️ Previous Release Archives

Archived previous releases and older standalone binaries are preserved under the [`release/previous/`](previous/) directory.

---

## 🧙 Official Install Wizard (Hath0r CLI + Hath0r MCP via Docker)

The **Hath0r Install Wizard** is the canonical release installer for operators and developers downloading Hath0r. It:
1. Checks and installs missing host dependencies (Python 3.10+, `pipx`, Git, `curl`, Docker Engine, Docker Compose v2) and starts the Docker daemon.
2. Installs the `hath0r` CLI globally (`pipx`, standalone binary, or `pip`) and verifies `PATH`.
3. Stages the `Hath0r-MCP` `Dockerfile`, `docker-compose.yml`, and canonical knowledgebase (`~/.hath0r/mcp` or workspace sibling `hath0r-mcp`).
4. Creates the external `hath0r-net` Docker network (`com.hath0r.*` labels) and launches the `Hath0r-MCP` container (`127.0.0.1:38083:8083`).
5. Verifies `/health` and `/ready` endpoints, configures `.hath0r/mcp.json`, and writes `~/.hath0r/install/INSTALL_RECEIPT.json`.

```bash
# Run the Install Wizard directly:
./release/install-wizard.sh
# or:
python3 scripts/install_hath0r.py

# Preview all actions without modifying your machine:
./release/install-wizard.sh --dry-run

# Or run from an installed hath0r CLI at any time:
hath0r install-wizard check
hath0r install-wizard run
hath0r install-wizard status
hath0r install-wizard repair
```

---

## 🚀 Quick Start (Zero Setup Standalone Binary)

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
