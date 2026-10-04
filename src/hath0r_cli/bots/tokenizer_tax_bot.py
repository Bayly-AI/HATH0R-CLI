"""FinOps Tokenizer Tax Auditor Bot for HATH0R CLI."""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TokenizerTaxBot:
    """Audits subword tokenizer tax across multilingual corpora and calculates ViT patch budgets."""

    cwd: Path = field(default_factory=Path.cwd)

    # Unicode ranges and typical expansion factors relative to English Latin
    SCRIPT_EXPANSION_FACTORS: Dict[str, float] = field(
        default_factory=lambda: {
            "LATIN": 1.00,
            "CYRILLIC": 1.85,
            "GREEK": 1.90,
            "HEBREW": 2.40,
            "ARABIC": 3.45,
            "DEVANAGARI": 4.10,
            "BENGALI": 4.25,
            "TAMIL": 4.60,
            "CJK": 2.30,
            "HIRAGANA": 2.70,
            "KATAKANA": 2.70,
            "HANGUL": 2.80,
            "THAI": 4.80,
            "COMMON": 1.00,
            "UNKNOWN": 1.50,
        }
    )

    def classify_character_script(self, char: str) -> str:
        """Classify a single Unicode character into its script family."""
        cp = ord(char)
        if 0x0041 <= cp <= 0x005A or 0x0061 <= cp <= 0x007A or 0x00C0 <= cp <= 0x024F:
            return "LATIN"
        if 0x0400 <= cp <= 0x04FF:
            return "CYRILLIC"
        if 0x0370 <= cp <= 0x03FF:
            return "GREEK"
        if 0x0590 <= cp <= 0x05FF:
            return "HEBREW"
        if 0x0600 <= cp <= 0x06FF or 0x0750 <= cp <= 0x077F:
            return "ARABIC"
        if 0x0900 <= cp <= 0x097F:
            return "DEVANAGARI"
        if 0x0980 <= cp <= 0x09FF:
            return "BENGALI"
        if 0x0B80 <= cp <= 0x0BFF:
            return "TAMIL"
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            return "CJK"
        if 0x3040 <= cp <= 0x309F:
            return "HIRAGANA"
        if 0x30A0 <= cp <= 0x30FF:
            return "KATAKANA"
        if 0xAC00 <= cp <= 0xD7AF:
            return "HANGUL"
        if 0x0E00 <= cp <= 0x0E7F:
            return "THAI"
        category = unicodedata.category(char)
        if category.startswith("Z") or category.startswith("P") or category.startswith("N"):
            return "COMMON"
        return "UNKNOWN"

    def audit(
        self,
        text_or_path: str,
        vocab_size: int = 256_000,
        hidden_dim: int = 4096,
        precision_bytes: int = 2,
        cost_per_million_tokens: float = 5.0,
        patch_size: int = 16,
    ) -> Dict[str, Any]:
        """Perform a comprehensive Tokenizer Tax and ViT patch budget audit."""
        p = Path(text_or_path)
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="replace")
            source = str(p)
        else:
            text = text_or_path
            source = "raw_string"

        if not text:
            return {
                "success": False,
                "error": "Input text or file content cannot be empty.",
            }

        total_chars = len(text)
        script_counts: Dict[str, int] = {}
        for c in text:
            s = self.classify_character_script(c)
            script_counts[s] = script_counts.get(s, 0) + 1

        script_breakdown: List[Dict[str, Any]] = []
        weighted_expansion = 0.0
        counted_chars = 0

        for script, count in sorted(script_counts.items(), key=lambda x: x[1], reverse=True):
            pct = round((count / total_chars) * 100, 2)
            factor = self.SCRIPT_EXPANSION_FACTORS.get(script, 1.0)
            script_breakdown.append(
                {
                    "script": script,
                    "character_count": count,
                    "percentage": pct,
                    "expansion_factor": factor,
                }
            )
            if script != "COMMON":
                weighted_expansion += factor * count
                counted_chars += count

        avg_expansion = (weighted_expansion / counted_chars) if counted_chars > 0 else 1.0
        avg_expansion = max(1.0, round(avg_expansion, 2))

        # Baseline subword token estimates
        baseline_tokens = max(1, int(total_chars / 4.0))
        expanded_tokens = int(baseline_tokens * avg_expansion)
        token_tax_penalty = expanded_tokens - baseline_tokens

        # Serving VRAM parameter calculations: P_vocab = 2 * V * d_model
        vocab_params = 2 * vocab_size * hidden_dim
        vram_bytes = vocab_params * precision_bytes
        vram_gb = round(vram_bytes / 1e9, 2)

        # ViT Continuous Patch Budget: (H / P) * (W / P)
        # Default standard document page: 1024 x 768 rendered
        doc_w, doc_h = 768, 1024
        patches_x = math.ceil(doc_w / patch_size)
        patches_y = math.ceil(doc_h / patch_size)
        total_patches = patches_x * patches_y

        # FinOps Economics
        baseline_cost = round((baseline_tokens / 1_000_000) * cost_per_million_tokens, 4)
        actual_cost = round((expanded_tokens / 1_000_000) * cost_per_million_tokens, 4)
        tax_cost_excess = round(actual_cost - baseline_cost, 4)
        potential_savings_pct = (
            round(((actual_cost - baseline_cost) / actual_cost) * 100, 1) if actual_cost > 0 else 0.0
        )

        return {
            "success": True,
            "source": source,
            "total_characters": total_chars,
            "scripts_detected": len(script_counts),
            "script_breakdown": script_breakdown,
            "token_metrics": {
                "inflation_ratio": avg_expansion,
                "baseline_tokens_latin_equiv": baseline_tokens,
                "actual_subword_tokens": expanded_tokens,
                "tax_penalty_tokens": token_tax_penalty,
            },
            "vocab_vram_overhead": {
                "vocab_size": vocab_size,
                "hidden_dim": hidden_dim,
                "precision": "FP16" if precision_bytes == 2 else "FP32",
                "vocab_parameters": vocab_params,
                "vocab_vram_gb": vram_gb,
            },
            "vit_patch_budget": {
                "patch_size": f"{patch_size}x{patch_size}",
                "rendered_page_size": f"{doc_w}x{doc_h}",
                "total_continuous_patches": total_patches,
                "multilingual_normalized": True,
            },
            "finops_impact": {
                "baseline_cost_usd": baseline_cost,
                "actual_cost_usd": actual_cost,
                "tax_cost_excess_usd": tax_cost_excess,
                "potential_cost_savings_pct": potential_savings_pct,
            },
        }
