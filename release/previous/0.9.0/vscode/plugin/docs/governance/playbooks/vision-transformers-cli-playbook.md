# Playbook: Vision Transformers (ViT) & Multimodal CLI Operations

> Operational Playbook for Hath0r Multimodal Perception & Visual Ingestion  
> Product: `HATH0R-CLI` · Group: `hath0r-opensource` · Issue: #219 · Framework Alignment: #149

---

## 📋 Overview

This playbook describes standard operating procedures for executing multimodal tasks, parsing visual documents, locating UI elements via visual grounding, and verifying vision provider connectivity.

---

## 🛠️ CLI Operations & Commands

### 1. Inspect an Image or Screenshot
Extract descriptions, detected visual objects, and embedded text from any image file:

```bash
hath0r vision inspect path/to/image.png
# Output structured JSON:
hath0r vision inspect path/to/image.png -o json
```

### 2. Parse Visual Documents & Architecture Diagrams
Extract structured layout, headings, diagrams, and tabular data from documents:

```bash
hath0r vision parse-doc path/to/architecture_diagram.png
# Provide specific extraction prompt:
hath0r vision parse-doc path/to/diagram.png --prompt "Extract database nodes and relationships"
```

### 3. UI Element Visual Grounding
Identify the coordinates and bounding box of a specific UI element:

```bash
hath0r vision ground path/to/screenshot.png --target "Login with Google button"
```

### 4. Generate Multimodal Embeddings
Compute cross-modal vector representation for visual RAG indexing:

```bash
hath0r vision embed path/to/diagram.png
```

### 5. Verify Vision Environment & Providers
Diagnose local and configured remote vision backends:

```bash
hath0r vision doctor
```

---

## ⚙️ Configuration (`cfg/vision.yaml`)

Specify local and remote provider preferences in `cfg/vision.yaml`:

```yaml
version: "1.0"
provider: "auto" # auto | ollama | remote | fallback
local:
  backend: "ollama"
  model: "llava"
  host: "http://localhost:11434"
remote:
  model: "gpt-4o"
embedding:
  model: "clip-vit-base-patch32"
  dimensions: 512
```
