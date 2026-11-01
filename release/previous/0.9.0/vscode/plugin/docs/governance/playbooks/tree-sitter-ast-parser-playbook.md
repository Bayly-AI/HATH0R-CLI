# Tree-Sitter & AST Code Intelligence Playbook

> Scope: **Developer & Operator Runbook for Code Outlining and AST Pruning**  
> Rule Reference: **CR-CLI-ENTRY-001**  
> Issue: **#236**

---

## 1. Quick Start

### Extracting a Compact File Outline
```bash
hath0r code outline src/hath0r_cli/cli.py
```

### Listing All File Symbols with Line Spans
```bash
hath0r code symbols src/hath0r_cli/cli.py
```

### Pre-Commit Syntax Validation
```bash
hath0r code validate src/hath0r_cli/cli.py
```

---

## 2. Structured JSON Output
```bash
hath0r --output json code outline src/hath0r_cli/cli.py
```

Sample output:
```json
{
  "file": "src/hath0r_cli/cli.py",
  "language": "python",
  "symbols": [
    {
      "name": "main",
      "type": "function",
      "signature": "def main() -> None",
      "line_start": 45,
      "line_end": 78,
      "docstring": "Main CLI entry point."
    }
  ]
}
```
