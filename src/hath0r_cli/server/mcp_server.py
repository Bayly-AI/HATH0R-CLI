"""FastMCP stdio server exposing HATH0R CLI capabilities to Claude Desktop and MCP clients."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None  # type: ignore[assignment,misc]


def get_claude_desktop_config_path() -> Path:
    """Return the platform-specific path to Claude Desktop configuration."""
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif sys.platform == "win32":
        app_data = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(app_data) / "Claude" / "claude_desktop_config.json"
    else:
        return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def install_claude_desktop_connector(
    server_name: str = "hath0r-cli",
    hath0r_binary: Optional[str] = None,
) -> Dict[str, Any]:
    """Register HATH0R CLI in Claude Desktop config file (~/Library/Application Support/Claude/claude_desktop_config.json)."""
    config_path = get_claude_desktop_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    binary_path = hath0r_binary or "/usr/local/bin/hath0r"
    if not Path(binary_path).exists():
        import shutil
        found = shutil.which("hath0r")
        if found:
            binary_path = found

    data: Dict[str, Any] = {}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}

    if "mcpServers" not in data:
        data["mcpServers"] = {}

    data["mcpServers"][server_name] = {
        "command": binary_path,
        "args": ["mcp", "serve"],
    }

    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {
        "success": True,
        "config_path": str(config_path),
        "server_name": server_name,
        "command": binary_path,
        "args": ["mcp", "serve"],
    }


def create_mcp_server(name: str = "hath0r-cli") -> FastMCP:
    """Create and configure the Hath0r FastMCP server with tools."""
    if FastMCP is None:
        raise RuntimeError("mcp package is not installed. Install with `pip install 'mcp<2'`.")

    mcp = FastMCP(name=name)

    @mcp.tool()
    def hath0r_cli(command: str) -> str:
        """Run any HATH0R CLI command (e.g. 'doctor', 'optimize taguchi --array L9 -f temp', 'finops tokenizer-tax "hello"').
        
        Args:
            command: The command line arguments to pass to hath0r (without 'hath0r' prefix).
        """
        import shlex
        args = shlex.split(command)
        cmd = [sys.executable, "-m", "hath0r_cli"] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            return res.stdout if res.stdout else res.stderr
        except Exception as exc:
            return f"Error executing hath0r command: {exc}"

    @mcp.tool()
    def hath0r_doctor() -> str:
        """Run comprehensive HATH0R health diagnostics across the suite, control tower, and knowledgebase."""
        cmd = [sys.executable, "-m", "hath0r_cli", "-o", "json", "doctor"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        return res.stdout if res.stdout else res.stderr

    @mcp.tool()
    def hath0r_optimize_taguchi(
        array: str = "L9",
        factors: Optional[List[str]] = None,
        snr_values: Optional[List[float]] = None,
        criterion: str = "smaller_is_better",
        loss_k: Optional[float] = None,
        target_m: Optional[float] = None,
        measured_y: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate Taguchi orthogonal design array (L4, L8, L9, L12, L18), calculate SNR, and compute Quality Loss.
        
        Args:
            array: Orthogonal array name ('L4', 'L8', 'L9', 'L12', 'L18').
            factors: Names of parameter factors to evaluate.
            snr_values: Measured observations to compute Signal-to-Noise Ratio (SNR) in dB.
            criterion: 'smaller_is_better', 'larger_is_better', or 'nominal_is_best'.
            loss_k: Financial loss sensitivity coefficient k in L(y) = k(y-m)^2.
            target_m: Nominal specification target value.
            measured_y: Actual observed quality characteristic value.
        """
        from hath0r_cli.bots.taguchi_bot import TaguchiBot

        bot = TaguchiBot()
        factor_list = factors or ["factor_1", "factor_2"]
        design = bot.generate_orthogonal_design(factor_list, array_type=array)

        res: Dict[str, Any] = {
            "design": design.to_dict(),
        }

        if snr_values:
            snr = bot.calculate_snr(snr_values, criterion=criterion)
            res["snr"] = {
                "values": snr_values,
                "criterion": criterion,
                "snr_db": snr,
            }

        if loss_k is not None and target_m is not None and measured_y is not None:
            loss = bot.calculate_quality_loss(measured_y, target=target_m, loss_k=loss_k)
            res["quality_loss"] = {
                "loss_usd": loss,
                "loss_k": loss_k,
                "target_m": target_m,
                "measured_y": measured_y,
            }

        return res

    @mcp.tool()
    def hath0r_finops_tokenizer_tax(
        text: str,
        vocab_size: int = 256000,
        hidden_dim: int = 4096,
        precision: str = "fp16",
    ) -> Dict[str, Any]:
        """Audit token inflation across 14 Unicode scripts, serving VRAM overhead, and ViT continuous patch budgets.
        
        Args:
            text: Input prompt, document text, or file path to evaluate.
            vocab_size: Vocabulary dictionary size (default: 256,000 tokens).
            hidden_dim: Model hidden representation dimension (default: 4096).
            precision: Model weight precision ('fp16', 'bf16', 'fp32', 'int8').
        """
        from hath0r_cli.bots.tokenizer_tax_bot import TokenizerTaxBot

        bot = TokenizerTaxBot(vocab_size=vocab_size, hidden_dim=hidden_dim, precision=precision)
        return bot.audit_text(text)

    @mcp.tool()
    def hath0r_vision_parse_doc(
        file_path: str,
        pixel_native: bool = True,
    ) -> Dict[str, Any]:
        """Parse documents, invoices, and spreadsheets directly into 2D tabular cell matrices without OCR.
        
        Args:
            file_path: Absolute or relative path to the image or document file.
            pixel_native: Use pixel-native visual patch extraction preserving spatial coordinates.
        """
        from hath0r_cli.bots.vision_bot import VisionBot

        bot = VisionBot()
        return bot.parse_document(file_path, pixel_native=pixel_native)

    @mcp.tool()
    def hath0r_vision_ground(
        image_path: str,
        target: str,
        playwright: bool = True,
        action: str = "click",
    ) -> Dict[str, Any]:
        """Visually ground a natural language target description on an interface screenshot and emit Playwright actions.
        
        Args:
            image_path: Path to the screenshot or UI image.
            target: Natural language description of the element to interact with (e.g. 'Submit PO').
            playwright: Generate DOM-independent coordinate action step.
            action: Action type ('click', 'hover', 'fill', 'press').
        """
        from hath0r_cli.bots.vision_bot import VisionBot

        bot = VisionBot()
        return bot.ground_element(image_path, target=target, emit_playwright=playwright, action=action)

    @mcp.tool()
    def hath0r_kb_search(query: str, limit: int = 5) -> Dict[str, Any]:
        """Search canonical Hath0r knowledgebase, playbooks, architecture decision records, and governance rules.
        
        Args:
            query: Keywords or conceptual query string.
            limit: Maximum number of search results to return (1-20).
        """
        cmd = [sys.executable, "-m", "hath0r_cli", "-o", "json", "kb", "search", query, "--limit", str(limit)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        try:
            return json.loads(res.stdout)
        except Exception:
            return {"raw_output": res.stdout, "error": res.stderr}

    return mcp
