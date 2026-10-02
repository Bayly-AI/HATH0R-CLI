# HATH0R CLI Anthropic / Claude Plugin

The official Anthropic Claude plugin for the **HATH0R CLI Operator** (`hath0r`).

## Capabilities Included
- **Operator CLI Gateway (`hath0r_cli`)**: Run CLI workflows directly from Claude.
- **System Doctor (`hath0r_doctor`)**: Verify multi-repo governance, control tower status, and canonical KB health.
- **Taguchi Parameter Optimization (`hath0r_optimize_taguchi`)**: Generate balanced orthogonal design arrays ($L_4..L_{18}$), compute Signal-to-Noise Ratio (SNR), and evaluate quadratic quality loss.
- **FinOps Multilingual Tokenizer Tax Auditor (`hath0r_finops_tokenizer_tax`)**: Benchmark subword token inflation across 14 Unicode scripts, estimate idle serving VRAM ($P_{vocab} = 2 \cdot V \cdot d_{model}$), and budget continuous 2D visual patches.
- **Pixel-Native 2D Document Parsing (`hath0r_vision_parse_doc`)**: Parse complex financial spreadsheets and invoices into spatial cell matrices without OCR.
- **Self-Healing UI Element Grounding (`hath0r_vision_ground`)**: Locate visual controls from natural language descriptions and emit Playwright-ready automation steps.
- **Knowledgebase Semantic Search (`hath0r_kb_search`)**: Query canonical governance standards and playbooks.

## Usage
This plugin runs through Model Context Protocol (MCP) using stdio transport:
```bash
hath0r mcp serve
```
