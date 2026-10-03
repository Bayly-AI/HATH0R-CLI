"""Token Check Workflow Bot for HATH0R CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from hath0r_cli.bots.token_telemetry_bot import TokenTelemetryCLIBot


@dataclass
class TokenCheckWorkflowBot:
    """Executes the 'token check' workflow, generating 90-day FinOps usage analytics and HTML dashboard artifacts."""

    cwd: Path = field(default_factory=Path.cwd)

    def run_token_check(
        self,
        user_id: str = "raybayly",
        days: int = 90,
        artifact_dir: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Execute complete token check workflow for a user."""
        bot = TokenTelemetryCLIBot(cwd=self.cwd)
        hist = bot.histogram(user_id=user_id, bins_count=10)

        tot_recs = hist.get("total_records", 0)
        tot_tok = hist.get("total_tokens", 0)
        tot_cost = hist.get("total_cost_usd", 0.0)
        stats = hist.get("stats", {})
        bins = hist.get("bins", [])
        model_dist = hist.get("model_distribution", {})

        # Compute prompt/completion breakdown
        records = bot.list_records(user_id=user_id, limit=10_000)
        prompt_tok = sum(r.get("prompt_tokens", 0) for r in records)
        completion_tok = sum(r.get("completion_tokens", 0) for r in records)

        # Build ASCII Histogram Table
        ascii_lines = [
            "Range           Count      %     Cumulative %  Distribution",
            "-------------------------------------------------------------------------",
        ]
        for b in bins:
            st = b.get("bin_start", 0)
            en = b.get("bin_end", 0)
            c = b.get("count", 0)
            pct = b.get("percentage", 0.0)
            cum = b.get("cumulative_percentage", 0.0)
            bar = b.get("ascii_bar", "")
            range_str = f"[{st:.1f} - {en:.1f}]".ljust(15)
            ascii_lines.append(f"{range_str} {str(c).rjust(5)}   {pct:5.1f}%     {cum:5.1f}%      {bar}")

        ascii_histogram = "\n".join(ascii_lines)

        # Build Model Breakdown Table
        model_lines = [
            "| Model | Interactions | Total Tokens | Cost (USD) | % of Total Cost |",
            "| :--- | :--- | :--- | :--- | :--- |",
        ]
        for m, data in model_dist.items():
            m_cnt = data.get("count", 0)
            m_tok = data.get("tokens", 0)
            m_cost = data.get("cost_usd", 0.0)
            m_pct = (m_cost / tot_cost * 100.0) if tot_cost > 0 else 0.0
            model_lines.append(f"| `{m}` | {m_cnt} | {m_tok} | ${m_cost:.6f} | {m_pct:.1f}% |")

        model_breakdown_table = "\n".join(model_lines)

        # Write HTML Artifact if directory supplied
        html_artifact_path = None
        embed_tag = ""
        if artifact_dir:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            html_path = artifact_dir / "finops_token_histogram.html"
            html_content = self._generate_html_dashboard(
                user_id=user_id,
                days=days,
                tot_recs=tot_recs,
                tot_tok=tot_tok,
                prompt_tok=prompt_tok,
                completion_tok=completion_tok,
                tot_cost=tot_cost,
                stats=stats,
                bins=bins,
                model_dist=model_dist,
            )
            html_path.write_text(html_content, encoding="utf-8")
            html_artifact_path = str(html_path)
            embed_tag = f'<agent-embed src="file://{html_artifact_path}"></agent-embed>'

        # Build final Markdown Report
        markdown_report = f"""### FinOps Token Telemetry & {days}-Day Usage Histogram

Your token usage telemetry ledger tracks every agent interaction for user **`{user_id}`**.

{embed_tag}

---

### 📊 Estimated Usage Summary (Trailing {days} Days)

- **Total Recorded Interactions**: {tot_recs} requests
- **Total Prompt Tokens**: {prompt_tok} tokens
- **Total Completion Tokens**: {completion_tok} tokens
- **Total Tokens Consumed**: **{tot_tok} tokens**
- **Estimated Total Cost**: **${tot_cost:.4f} USD**

---

### 📈 Statistical Distribution Metrics (`prompt_tokens`)

| Metric | Value |
| :--- | :--- |
| **Minimum** | {stats.get('min', 0)} tokens |
| **Maximum** | {stats.get('max', 0)} tokens |
| **Mean (Average)** | {stats.get('mean', 0)} tokens |
| **Median ($p_{{50}}$)** | {stats.get('median', 0)} tokens |
| **$p_{{95}}$ Percentile** | {stats.get('p95', 0)} tokens |
| **$p_{{99}}$ Percentile** | {stats.get('p99', 0)} tokens |
| **Standard Deviation** | {stats.get('std_dev', 0)} |

#### ASCII Distribution Histogram
```text
{ascii_histogram}
```

---

### 🤖 Model Breakdown

{model_breakdown_table}

---

### 💻 Operator CLI Command

You can query or export token telemetry directly from the CLI:

```bash
hath0r finops tokens check --user {user_id} --days {days}
```
"""

        return {
            "success": True,
            "user_id": user_id,
            "days": days,
            "total_records": tot_recs,
            "total_tokens": tot_tok,
            "prompt_tokens": prompt_tok,
            "completion_tokens": completion_tok,
            "total_cost_usd": tot_cost,
            "stats": stats,
            "bins": bins,
            "model_distribution": model_dist,
            "markdown_report": markdown_report,
            "html_artifact_path": html_artifact_path,
            "embed_tag": embed_tag,
        }

    def _generate_html_dashboard(
        self,
        user_id: str,
        days: int,
        tot_recs: int,
        tot_tok: int,
        prompt_tok: int,
        completion_tok: int,
        tot_cost: float,
        stats: Dict[str, Any],
        bins: list,
        model_dist: Dict[str, Any],
    ) -> str:
        """Generate Tailwind CSS dashboard HTML string for FinOps token telemetry."""
        bin_rows = []
        for b in bins:
            st = b.get("bin_start", 0)
            en = b.get("bin_end", 0)
            c = b.get("count", 0)
            pct = b.get("percentage", 0.0)
            bar_width = pct if pct > 0 else 0
            if c > 0:
                bin_rows.append(f"""
      <div class="flex items-center text-xs gap-3">
        <div class="w-24 text-[var(--muted-foreground,#94a3b8)] font-mono">[{st:.1f} - {en:.1f}]</div>
        <div class="flex-1 bg-[var(--background,#0f172a)] h-6 rounded overflow-hidden border border-[var(--border,#334155)] flex items-center px-1">
          <div class="bg-[var(--primary,#38bdf8)] h-4 rounded transition-all duration-500 flex items-center justify-end px-2 text-[10px] font-bold text-slate-900" style="width: {bar_width}%;">
            {c} ({pct:.1f}%)
          </div>
        </div>
      </div>""")
            else:
                bin_rows.append(f"""
      <div class="flex items-center text-xs gap-3 opacity-50">
        <div class="w-24 text-[var(--muted-foreground,#94a3b8)] font-mono">[{st:.1f} - {en:.1f}]</div>
        <div class="flex-1 bg-[var(--background,#0f172a)] h-6 rounded border border-[var(--border,#334155)] flex items-center px-3 text-[11px] text-[var(--muted-foreground,#94a3b8)] italic">
          0 interactions
        </div>
      </div>""")

        bin_rows_html = "\n".join(bin_rows)

        model_rows = []
        for m, data in model_dist.items():
            m_cnt = data.get("count", 0)
            m_tok = data.get("tokens", 0)
            m_cost = data.get("cost_usd", 0.0)
            m_pct = (m_cost / tot_cost * 100.0) if tot_cost > 0 else 0.0
            model_rows.append(f"""
          <tr class="hover:bg-[var(--background,#0f172a)]">
            <td class="py-2.5 px-3 font-semibold text-[var(--foreground,#f8fafc)]">{m}</td>
            <td class="py-2.5 px-3">{m_cnt}</td>
            <td class="py-2.5 px-3">{m_tok}</td>
            <td class="py-2.5 px-3 text-emerald-400">${m_cost:.6f}</td>
            <td class="py-2.5 px-3 font-bold">{m_pct:.1f}%</td>
          </tr>""")

        model_rows_html = "\n".join(model_rows)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>FinOps Token Telemetry & {days}-Day Histogram</title>
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
  <style>
    body {{
      background-color: var(--background, #0f172a);
      color: var(--foreground, #f8fafc);
      font-family: system-ui, -apple-system, sans-serif;
    }}
  </style>
</head>
<body class="p-6 max-w-5xl mx-auto space-y-6">

  <div class="flex items-center justify-between border-b border-[var(--border,#334155)] pb-4">
    <div>
      <h1 class="text-2xl font-bold text-[var(--foreground,#f8fafc)] flex items-center gap-2">
        <span>📊</span> FinOps Token Telemetry & {days}-Day Histogram
      </h1>
      <p class="text-sm text-[var(--muted-foreground,#94a3b8)] mt-1">
        User: <span class="font-semibold text-[var(--primary,#38bdf8)]">{user_id}</span> • Period: Trailing {days} Days
      </p>
    </div>
    <div>
      <span class="inline-block px-3 py-1 text-xs font-medium rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        Status: Active Tracking
      </span>
    </div>
  </div>

  <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
    <div class="bg-[var(--card,#1e293b)] p-4 rounded-xl border border-[var(--border,#334155)] shadow-sm">
      <div class="text-xs font-medium text-[var(--muted-foreground,#94a3b8)] uppercase tracking-wider">Total Recorded Tokens</div>
      <div class="text-2xl font-bold text-[var(--foreground,#f8fafc)] mt-2">{tot_tok}</div>
      <div class="text-xs text-[var(--muted-foreground,#94a3b8)] mt-1">{prompt_tok} prompt • {completion_tok} completion</div>
    </div>

    <div class="bg-[var(--card,#1e293b)] p-4 rounded-xl border border-[var(--border,#334155)] shadow-sm">
      <div class="text-xs font-medium text-[var(--muted-foreground,#94a3b8)] uppercase tracking-wider">Estimated Spend (USD)</div>
      <div class="text-2xl font-bold text-emerald-400 mt-2">${tot_cost:.4f}</div>
      <div class="text-xs text-[var(--muted-foreground,#94a3b8)] mt-1">Tier pricing benchmarks</div>
    </div>

    <div class="bg-[var(--card,#1e293b)] p-4 rounded-xl border border-[var(--border,#334155)] shadow-sm">
      <div class="text-xs font-medium text-[var(--muted-foreground,#94a3b8)] uppercase tracking-wider">Total Interactions</div>
      <div class="text-2xl font-bold text-[var(--foreground,#f8fafc)] mt-2">{tot_recs}</div>
      <div class="text-xs text-[var(--muted-foreground,#94a3b8)] mt-1">100% logged</div>
    </div>

    <div class="bg-[var(--card,#1e293b)] p-4 rounded-xl border border-[var(--border,#334155)] shadow-sm">
      <div class="text-xs font-medium text-[var(--muted-foreground,#94a3b8)] uppercase tracking-wider">P95 / P99 Token Floor</div>
      <div class="text-2xl font-bold text-[var(--primary,#38bdf8)] mt-2">{stats.get('p95', 0)} / {stats.get('p99', 0)}</div>
      <div class="text-xs text-[var(--muted-foreground,#94a3b8)] mt-1">Mean: {stats.get('mean', 0)} • Median: {stats.get('median', 0)}</div>
    </div>
  </div>

  <div class="bg-[var(--card,#1e293b)] p-6 rounded-xl border border-[var(--border,#334155)] space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-lg font-semibold text-[var(--foreground,#f8fafc)]">
        📈 Token Usage Histogram Bins
      </h2>
      <span class="text-xs text-[var(--muted-foreground,#94a3b8)]">10 Equal-Width Bins</span>
    </div>

    <div class="space-y-2">
{bin_rows_html}
    </div>
  </div>

  <div class="bg-[var(--card,#1e293b)] p-6 rounded-xl border border-[var(--border,#334155)] space-y-4">
    <h2 class="text-lg font-semibold text-[var(--foreground,#f8fafc)]">
      🤖 Model Breakdown
    </h2>

    <div class="overflow-x-auto">
      <table class="w-full text-xs text-left border-collapse">
        <thead>
          <tr class="border-b border-[var(--border,#334155)] text-[var(--muted-foreground,#94a3b8)] uppercase tracking-wider">
            <th class="py-2 px-3">Model</th>
            <th class="py-2 px-3">Interactions</th>
            <th class="py-2 px-3">Total Tokens</th>
            <th class="py-2 px-3">Cost (USD)</th>
            <th class="py-2 px-3">% of Total Cost</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-[var(--border,#334155)] font-mono">
{model_rows_html}
        </tbody>
      </table>
    </div>
  </div>

</body>
</html>
"""
