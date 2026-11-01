# Playbook: Release Binary Packaging, Rotation & Cross-Repo Sync

> Operational Playbook for Operators and Release Engineers  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #217

---

## 📋 Overview

This playbook provides actionable procedures for building CLI release binaries, archiving previous versions into `release/previous/`, and synchronizing release folders between `HATH0R-CLI` and `hath0r-framework`.

---

## 🛠️ Commands & Automation

### 1. Build and Rotate Release Binaries
To compile the standalone binary for the current host, rotate previous binaries into `release/previous/<version>/`, and update checksums:

```bash
hath0r release build
```

Or via direct script:
```bash
python3 scripts/build_release_binaries.py
```

### 2. Dry-Run Verification
To preview the rotation and build actions without altering files:
```bash
hath0r release build --dry-run
```

### 3. Synchronize Release Artifacts to Framework
To explicitly push active release binaries and archives to the framework directory:
```bash
hath0r release sync
```

### 4. Recalculate Checksums
To regenerate SHA-256 manifests across `release/` and all archived directories in `release/previous/`:
```bash
hath0r release build --checksums-only
```

---

## 🧪 Verification & Acceptance Criteria

1. **Active Artifact Verification**:
   ```bash
   shasum -a 256 -c release/CHECKSUMS.sha256
   ```

2. **Previous Archive Verification**:
   ```bash
   cd release/previous/<archived-version>
   shasum -a 256 -c CHECKSUMS.sha256
   ```

3. **Dual-Repo Consistency**:
   Verify that `release/` files in `HATH0R-CLI` match `hath0r-framework/release/`.
