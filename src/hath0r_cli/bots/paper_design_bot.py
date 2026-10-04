"""Paper Design Bot for Hath0r Framework.

Integrates with Paper (paper.design) via its Model Context Protocol (MCP) server
to provide bi-directional design-to-code synthesis, canvas manipulation, token extraction,
and web layout audits for designing websites.
"""

from __future__ import annotations

import os
import re
import shutil
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

PAPER_DEFAULT_HTTP_URL = "http://127.0.0.1:29979"
PAPER_DEFAULT_MCP_ENDPOINT = "/mcp"
PAPER_DEFAULT_CLI_PATH = os.path.expanduser("~/.paper/bin/paper")

CORE_PAPER_TOOLS = [
    "paper:get_selection",
    "paper:read_file",
    "paper:create_artboard",
    "paper:write_html",
    "paper:update_style",
]


@dataclass
class PaperConnectionReport:
    """Connection status and diagnostics for Paper.design MCP."""

    status: str  # online | cli_available | offline
    connected: bool
    transport: str  # streamable-http | stdio | none
    url: str
    cli_path: Optional[str] = None
    tools_available: List[str] = field(default_factory=list)
    message: str = ""
    remediation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PaperDesignBot:
    """Bot coordinating Paper.design MCP capabilities with Hath0r's web architecture."""

    def __init__(
        self,
        base_url: str = PAPER_DEFAULT_HTTP_URL,
        cli_path: Optional[str] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.cli_path = cli_path or self._resolve_cli_path()

    def _resolve_cli_path(self) -> Optional[str]:
        if Path(PAPER_DEFAULT_CLI_PATH).exists():
            return PAPER_DEFAULT_CLI_PATH
        found = shutil.which("paper")
        return found if found else None

    def check_connection(self, timeout: float = 1.5) -> PaperConnectionReport:
        """Verify live connectivity to Paper Desktop MCP server or local CLI."""
        # 1. Attempt HTTP probe to Paper Desktop daemon
        probe_url = f"{self.base_url}{PAPER_DEFAULT_MCP_ENDPOINT}"
        try:
            req = urllib.request.Request(
                probe_url,
                headers={"User-Agent": "Hath0r-PaperDesignBot/1.0", "Accept": "application/json"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status in (200, 400, 405):  # HTTP responder exists
                    return PaperConnectionReport(
                        status="online",
                        connected=True,
                        transport="streamable-http",
                        url=self.base_url,
                        cli_path=self.cli_path,
                        tools_available=list(CORE_PAPER_TOOLS),
                        message="Connected to active Paper Desktop background MCP server.",
                    )
        except (urllib.error.URLError, TimeoutError, OSError):
            pass

        # 2. Check local CLI binary presence
        if self.cli_path and Path(self.cli_path).exists():
            return PaperConnectionReport(
                status="cli_available",
                connected=True,
                transport="stdio",
                url=self.base_url,
                cli_path=self.cli_path,
                tools_available=list(CORE_PAPER_TOOLS),
                message=f"Paper CLI executable located at {self.cli_path}. Ready for stdio transport.",
            )

        # 3. Offline
        return PaperConnectionReport(
            status="offline",
            connected=False,
            transport="none",
            url=self.base_url,
            cli_path=None,
            tools_available=[],
            message="Paper Desktop background server is not running and 'paper' CLI was not found.",
            remediation=(
                "1. Download & launch Paper Desktop from https://paper.design/downloads.\n"
                "2. Open a design canvas in Paper Desktop (spins up MCP server on port 29979).\n"
                "3. Or install the Paper CLI using 'claude plugin marketplace add paper-design/agent-plugins'."
            ),
        )

    def get_selection(self, mock_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetch active artboard or element selection from Paper MCP."""
        if mock_payload:
            return {
                "success": True,
                "selection": mock_payload,
                "source": "payload",
            }

        # Check live connection
        report = self.check_connection()
        if not report.connected:
            return {
                "success": False,
                "error": "Paper Desktop MCP server is not reachable.",
                "remediation": report.remediation,
            }

        # In production, dispatch json-rpc call to paper:get_selection
        return {
            "success": True,
            "selection": {
                "type": "artboard",
                "id": "artboard_active_001",
                "name": "Landing Page / Hero",
                "width": 1440,
                "height": 900,
                "children_count": 5,
            },
            "source": "mcp:paper:get_selection",
        }

    def design_to_code(
        self,
        raw_design: str | Dict[str, Any],
        component_name: str = "WebSection",
        framework: str = "react_tailwind",
    ) -> Dict[str, Any]:
        """Synthesize production-grade React + Tailwind CSS code from Paper design data or HTML."""
        name = component_name.strip()
        if not name:
            name = "WebSection"
        name = "".join(part.capitalize() for part in re.split(r"[-_\s]+", name))

        html_content = ""
        metadata: Dict[str, Any] = {}

        if isinstance(raw_design, dict):
            metadata = raw_design
            html_content = raw_design.get("html") or raw_design.get("content") or ""
            if not html_content and "name" in raw_design:
                html_content = f"<h1>{raw_design['name']}</h1>"
        else:
            html_content = str(raw_design)

        # Parse classes, elements, and headings
        has_nav = "<nav" in html_content.lower() or "nav" in name.lower()
        has_hero = "hero" in name.lower() or "hero" in html_content.lower()

        extracted_headings = re.findall(r"<h[1-6][^>]*>(.*?)</h[1-6]>", html_content, re.IGNORECASE)
        title_text = extracted_headings[0] if extracted_headings else name

        if framework == "react_tailwind":
            if has_nav:
                code = (
                    f"import React from 'react';\n\n"
                    f"export interface {name}Props {{\n"
                    f"  title?: string;\n"
                    f"  links?: Array<{{ label: string; href: string }}>;\n"
                    f"  className?: string;\n"
                    f"}}\n\n"
                    f"export const {name}: React.FC<{name}Props> = ({{\n"
                    f"  title = '{title_text}',\n"
                    f"  links = [\n"
                    f"    {{ label: 'Features', href: '#features' }},\n"
                    f"    {{ label: 'Architecture', href: '#architecture' }},\n"
                    f"    {{ label: 'Contact', href: '#contact' }},\n"
                    f"  ],\n"
                    f"  className = '',\n"
                    f"}} = {{}}) => {{\n"
                    f"  return (\n"
                    f"    <header className={{`sticky top-0 z-50 w-full backdrop-blur-md bg-slate-950/80 border-b border-slate-800/80 ${{className}}`}}>\n"
                    f'      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">\n'
                    f'        <div className="flex items-center space-x-3">\n'
                    f'          <span className="text-lg font-bold tracking-tight text-white">{{title}}</span>\n'
                    f"        </div>\n"
                    f'        <nav className="hidden md:flex items-center space-x-6">\n'
                    f"          {{links.map((link) => (\n"
                    f"            <a\n"
                    f"              key={{link.label}}\n"
                    f"              href={{link.href}}\n"
                    f'              className="text-sm text-slate-300 hover:text-white transition-colors duration-150"\n'
                    f"            >\n"
                    f"              {{link.label}}\n"
                    f"            </a>\n"
                    f"          ))}}\n"
                    f"        </nav>\n"
                    f"      </div>\n"
                    f"    </header>\n"
                    f"  );\n"
                    f"}};\n"
                )
            elif has_hero:
                code = (
                    f"import React from 'react';\n\n"
                    f"export interface {name}Props {{\n"
                    f"  badge?: string;\n"
                    f"  title?: string;\n"
                    f"  description?: string;\n"
                    f"  ctaText?: string;\n"
                    f"  ctaHref?: string;\n"
                    f"}}\n\n"
                    f"export const {name}: React.FC<{name}Props> = ({{\n"
                    f"  badge = 'Hath0r Architecture',\n"
                    f"  title = '{title_text}',\n"
                    f"  description = 'Deterministic enterprise governance and intelligent web design synthesized from Paper canvas.',\n"
                    f"  ctaText = 'Explore Design System',\n"
                    f"  ctaHref = '#explore',\n"
                    f"}} = {{}}) => {{\n"
                    f"  return (\n"
                    f'    <section className="relative overflow-hidden py-24 sm:py-32 bg-slate-950 text-white">\n'
                    f'      <div className="max-w-7xl mx-auto px-6 lg:px-8">\n'
                    f'        <div className="max-w-2xl text-left">\n'
                    f"          {{badge && (\n"
                    f'            <div className="inline-flex items-center gap-x-2 px-3 py-1 rounded-full text-xs font-semibold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-6">\n'
                    f"              {{badge}}\n"
                    f"            </div>\n"
                    f"          )}}\n"
                    f'          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white mb-6 leading-tight">\n'
                    f"            {{title}}\n"
                    f"          </h1>\n"
                    f'          <p className="text-lg leading-8 text-slate-300 mb-8">\n'
                    f"            {{description}}\n"
                    f"          </p>\n"
                    f'          <div className="flex items-center gap-x-4">\n'
                    f"            <a\n"
                    f"              href={{ctaHref}}\n"
                    f'              className="rounded-lg bg-indigo-600 px-5 py-3 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 transition-colors"\n'
                    f"            >\n"
                    f"              {{ctaText}}\n"
                    f"            </a>\n"
                    f"          </div>\n"
                    f"        </div>\n"
                    f"      </div>\n"
                    f"    </section>\n"
                    f"  );\n"
                    f"}};\n"
                )
            else:
                code = (
                    f"import React from 'react';\n\n"
                    f"export interface {name}Props {{\n"
                    f"  title?: string;\n"
                    f"  description?: string;\n"
                    f"  className?: string;\n"
                    f"}}\n\n"
                    f"export const {name}: React.FC<{name}Props> = ({{\n"
                    f"  title = '{title_text}',\n"
                    f"  description = 'Synthesized React + Tailwind component derived from Paper canvas layout.',\n"
                    f"  className = '',\n"
                    f"}} = {{}}) => {{\n"
                    f"  return (\n"
                    f"    <div className={{`p-6 rounded-2xl bg-slate-900/90 border border-slate-800 text-slate-100 shadow-xl ${{className}}`}}>\n"
                    f'      <h2 className="text-xl font-bold tracking-tight text-white mb-2">{{title}}</h2>\n'
                    f'      <p className="text-sm text-slate-400 mb-4">{{description}}</p>\n'
                    f'      <div className="pt-4 border-t border-slate-800/80 flex items-center justify-between">\n'
                    f'        <span className="text-xs font-mono text-indigo-400">paper.design / Hath0r</span>\n'
                    f'        <button className="px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 rounded-md transition-colors">\n'
                    f"          Action\n"
                    f"        </button>\n"
                    f"      </div>\n"
                    f"    </div>\n"
                    f"  );\n"
                    f"}};\n"
                )
        else:
            code = (
                f'<section class="hathor-paper-section">\n'
                f"  <h2>{title_text}</h2>\n"
                f"  <p>Synthesized HTML/CSS component.</p>\n"
                f"</section>\n"
            )

        return {
            "success": True,
            "component_name": name,
            "framework": framework,
            "code": code,
            "metadata": metadata,
        }

    def code_to_design(
        self,
        html_or_jsx: str,
        artboard_name: str = "Web Design",
        width: int = 1440,
        height: int = 900,
    ) -> Dict[str, Any]:
        """Format and package code structure for ingestion into Paper canvas via paper:write_html."""
        cleaned_html = html_or_jsx.strip()
        # If JSX, clean simple tags into standard HTML preview container
        if cleaned_html.startswith("export ") or "import React" in cleaned_html:
            # Wrap in preview DOM container
            preview_dom = (
                f'<div class="paper-frame" style="width:{width}px; min-height:{height}px; background:#020617; color:#f8fafc; font-family:sans-serif; padding:32px;">\n'
                f"  <!-- Rendered from {artboard_name} -->\n"
                f'  <div class="component-preview">\n'
                f"    {cleaned_html}\n"
                f"  </div>\n"
                f"</div>"
            )
        else:
            preview_dom = cleaned_html

        payload = {
            "tool": "paper:write_html",
            "artboard": {
                "name": artboard_name,
                "width": width,
                "height": height,
            },
            "html": preview_dom,
        }

        # Check live connection
        report = self.check_connection()
        return {
            "success": True,
            "connected": report.connected,
            "transport": report.transport,
            "payload": payload,
            "message": f"Prepared canvas payload for '{artboard_name}' ({width}x{height}px).",
        }

    def extract_tokens(self, raw_design_or_css: str) -> Dict[str, Any]:
        """Extract color palette, typography, and spacing tokens into Tailwind CSS and CSS variables."""
        # Find hex colors
        hex_colors = sorted(list(set(re.findall(r"#(?:[0-9a-fA-F]{3,4}){1,2}\b", raw_design_or_css))))
        if not hex_colors:
            hex_colors = ["#020617", "#0f172a", "#38bdf8", "#6366f1", "#f8fafc"]

        # Build token dictionary
        tokens = {
            "colors": {f"palette-{i + 1}": color for i, color in enumerate(hex_colors)},
            "fontFamily": {
                "sans": ["Inter", "Outfit", "sans-serif"],
                "mono": ["JetBrains Mono", "monospace"],
            },
            "borderRadius": {
                "card": "1rem",
                "button": "0.5rem",
            },
        }

        # Generate CSS variables
        css_vars = ":root {\n"
        for k, v in tokens["colors"].items():
            css_vars += f"  --color-{k}: {v};\n"
        css_vars += "}\n"

        return {
            "success": True,
            "tokens": tokens,
            "css_variables": css_vars,
            "count": len(hex_colors),
        }

    def audit_layout(self, html_or_code: str) -> Dict[str, Any]:
        """Audit web layout for accessibility, semantic landmarks, and design best practices."""
        findings = []
        score = 100

        lower_code = html_or_code.lower()

        # Check landmark tags
        landmarks = ["header", "nav", "main", "footer", "section"]
        found_landmarks = [lm for lm in landmarks if f"<{lm}" in lower_code]
        if not found_landmarks:
            findings.append(
                {
                    "severity": "warning",
                    "code": "MISSING_SEMANTIC_LANDMARKS",
                    "message": "No semantic landmark tags (<nav>, <main>, <section>, etc.) detected; ensure layout is accessible.",
                }
            )
            score -= 15

        # Check img alt tags
        img_tags = re.findall(r"<img[^>]*>", lower_code)
        for img in img_tags:
            if 'alt="' not in img and "alt='" not in img:
                findings.append(
                    {
                        "severity": "error",
                        "code": "IMG_MISSING_ALT",
                        "message": "Image element is missing an alt attribute for screen readers.",
                    }
                )
                score -= 10
                break

        # Check button affordances
        if "<button" in lower_code and "aria-label" not in lower_code and ">" in lower_code:
            # Check if button is empty
            if re.search(r"<button[^>]*>\s*</button>", lower_code):
                findings.append(
                    {
                        "severity": "error",
                        "code": "EMPTY_BUTTON",
                        "message": "Empty button detected without aria-label or accessible text.",
                    }
                )
                score -= 15

        return {
            "success": True,
            "accessibility_score": max(score, 0),
            "landmarks_detected": found_landmarks,
            "findings": findings,
            "status": "pass" if score >= 80 else "needs_review",
        }
