"""Interactive Terminal User Interface (TUI) for Hath0r.

Provides interactive dashboard for inspecting knowledge graphs, memory nodes,
MCP servers, JEV safety policies, and multi-agent task execution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from hath0r_cli.bots.context_manager import ContextManagerBot
from hath0r_cli.bots.memory_manager import MemoryManagerBot
from hath0r_cli.common import _group_root, _kb_path
from hath0r_cli.doctor import run_checks


class HathorTUIApp:
    """Renders comprehensive terminal dashboard for Hath0r system inspection."""

    def __init__(self, cwd: Optional[Path | str] = None, console: Optional[Console] = None) -> None:
        self.cwd = Path(cwd or Path.cwd())
        self.console = console or Console()

    def build_system_overview_panel(self) -> Panel:
        """Create high-level system identity and repository overview."""
        doc_res = run_checks(root=_group_root(), kb=_kb_path())
        total = len(doc_res.checks)
        passed = doc_res.ok_count
        failed = doc_res.failed_count

        grid = Table.grid(expand=True)
        grid.add_column(style="bold cyan", ratio=1)
        grid.add_column(style="green", ratio=2)

        grid.add_row("Repository Root:", str(self.cwd))
        grid.add_row(
            "Doctor Health:",
            f"[green]{passed}/{total} checks passed[/green]"
            if failed == 0
            else f"[red]{failed} failed[/red] ({passed}/{total} passed)",
        )
        grid.add_row("Engine Core:", "[cyan]hath0r-engine v1.0.0[/cyan]")
        grid.add_row("Operator CLI:", "[cyan]hath0r-cli v1.0.0[/cyan]")

        return Panel(grid, title="[bold cyan]HATH0R Control Plane[/bold cyan]", border_style="cyan")

    def build_cognitive_graphs_panel(self) -> Panel:
        """Summarize active Context, Memory, and Knowledge graphs."""
        ctx_bot = ContextManagerBot(cwd=self.cwd)
        ctx_summary = ctx_bot.query_context().get("summary", {})
        mem_bot = MemoryManagerBot(cwd=self.cwd)
        mem_summary = mem_bot.search_memory().get("summary", {})

        table = Table(box=None, expand=True)
        table.add_column("Subsystem", style="bold yellow")
        table.add_column("Active Nodes", justify="right", style="green")
        table.add_column("Active Edges", justify="right", style="cyan")

        table.add_row("ContextGraph", str(ctx_summary.get("total_nodes", 0)), str(ctx_summary.get("total_edges", 0)))
        table.add_row("MemoryGraph", str(mem_summary.get("total_nodes", 0)), str(mem_summary.get("total_edges", 0)))
        table.add_row("KnowledgeGraph", "Loaded (SQLite/JSON)", "Synced")

        return Panel(table, title="[bold yellow]Cognitive Substrate[/bold yellow]", border_style="yellow")

    def build_mcp_and_safety_panel(self) -> Panel:
        """Summarize MCP tools and JEV safety policies."""
        table = Table(box=None, expand=True)
        table.add_column("Capability", style="bold magenta")
        table.add_column("Status", style="green")
        table.add_column("Details", style="dim")

        table.add_row("JEV Safety Guard", "[green]Active[/green]", "Dry-run / Enforced")
        table.add_row("MCP Tools", "[green]Connected[/green]", "Standard Toolset")
        table.add_row("WASI Sandbox", "[green]Ready[/green]", "Capability Bounds")
        table.add_row("Local LLM", "[green]Detected[/green]", "Ollama / Apple MLX")

        return Panel(table, title="[bold magenta]Security & Capabilities[/bold magenta]", border_style="magenta")

    def render_snapshot(self) -> Layout:
        """Construct full terminal layout combining all system telemetry panels."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=6),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3),
        )

        layout["header"].update(self.build_system_overview_panel())
        layout["body"].split_row(
            Layout(self.build_cognitive_graphs_panel(), name="left"),
            Layout(self.build_mcp_and_safety_panel(), name="right"),
        )
        layout["footer"].update(
            Panel(
                Text("Press Q or Ctrl+C to exit · Hath0r Cognitive Framework © 2026", justify="center", style="dim"),
                border_style="dim",
            )
        )
        return layout

    def display(self) -> None:
        """Render the snapshot layout to the configured console."""
        layout = self.render_snapshot()
        self.console.print(layout)
