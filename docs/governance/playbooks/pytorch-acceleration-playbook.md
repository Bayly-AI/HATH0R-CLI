# Playbook: PyTorch Hardware Acceleration & Local Neural Execution

> Operational Playbook for Hath0r PyTorch Engine & Multimodal Workflows  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #221 · Framework Alignment: #149

---

## 📋 Overview

This playbook provides actionable instructions for configuring, testing, and operating PyTorch-accelerated vision, embedding, and reranking workflows in Hath0r CLI.

---

## 🛠️ CLI Operations & Commands

### 1. Check PyTorch Runtime Diagnostics
Inspect available compute devices (Apple Silicon `mps`, CUDA, CPU), VRAM allocation, and PyTorch version:

```bash
hath0r vision doctor
```

### 2. Run Accelerated Vision Inspection
Inspect an image using native PyTorch on a specific device:

```bash
# Auto device selection (MPS on Mac, CUDA on Linux):
hath0r vision inspect path/to/image.png

# Explicit device selection:
hath0r vision inspect path/to/image.png --device mps
```

### 3. Generate Hardware-Accelerated Embeddings
Extract normalized 512-d cross-modal embedding vectors:

```bash
hath0r vision embed path/to/diagram.png --device mps
```

### 4. Locate UI Coordinates via Grounding
Ground UI elements using on-device neural bounding boxes:

```bash
hath0r vision ground path/to/ui.png --target "Login Button" --device mps
```

---

## ⚙️ Configuration (`cfg/vision.yaml`)

Configure PyTorch settings in `cfg/vision.yaml`:

```yaml
version: "1.0"
provider: "pytorch" # auto | pytorch | ollama | remote | fallback
pytorch:
  device: "auto"    # auto | mps | cuda | cpu
  precision: "fp16" # fp32 | fp16 | bf16
  embedding_model: "clip-vit-base-patch32"
  dimensions: 512
```
