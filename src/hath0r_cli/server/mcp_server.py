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
    import shutil

    config_path = get_claude_desktop_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Explicit paths are honored as-is so operators can register a planned install
    # location (and unit tests can pin a stable path without requiring the binary).
    if hath0r_binary:
        binary_path = hath0r_binary
    else:
        binary_path = "/usr/local/bin/hath0r"
        if not Path(binary_path).exists():
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

    if "hath0r-mcp" not in data["mcpServers"]:
        npx_bin = "/usr/local/bin/npx" if Path("/usr/local/bin/npx").exists() else (shutil.which("npx") or "npx")
        data["mcpServers"]["hath0r-mcp"] = {
            "command": npx_bin,
            "args": ["-y", "mcp-remote", "https://mcp.hath0r-cli.com/mcp"],
        }

    if "paper-design-mcp" not in data["mcpServers"]:
        paper_bin = os.path.expanduser("~/.paper/bin/paper")
        if not Path(paper_bin).exists():
            paper_bin = shutil.which("paper") or paper_bin
        data["mcpServers"]["paper-design-mcp"] = {
            "command": paper_bin,
            "args": ["mcp"],
        }

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


def _search_ray_index(query: str, source: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
    index_path = Path("/Users/raybayly/Development/Ray/mcp/data/indices/knowledge_index.json")
    if not index_path.is_file():
        return {"success": False, "error": "Ray knowledge index file not found.", "results": []}
    import re
    from collections import Counter
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_docs = data.get("documents", [])
        documents = raw_docs.values() if isinstance(raw_docs, dict) else raw_docs
        candidates = []
        for doc in documents:
            if source and str(doc.get("source", "")).lower() != source.lower():
                continue
            candidates.append(doc)

        query_terms = [t.lower() for t in re.findall(r"\w+", query)]
        if not query_terms:
            return {"success": True, "count": 0, "results": []}

        scored = []
        for doc in candidates:
            text = f"{doc.get('title', '')} {doc.get('content', '')} {doc.get('relative_path', '')}"
            words = [w.lower() for w in re.findall(r"\w+", text)]
            tf = Counter(words)
            score = sum(tf[q] for q in query_terms if q in tf)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, doc in scored[:limit]:
            content = doc.get("content", "")
            preview = content[:200] + "..." if len(content) > 200 else content
            results.append({
                "doc_id": doc.get("id"),
                "source": doc.get("source"),
                "title": doc.get("title"),
                "relative_path": doc.get("relative_path"),
                "score": score,
                "preview": preview,
            })
        return {"success": True, "count": len(results), "results": results}
    except Exception as exc:
        return {"success": False, "error": str(exc), "results": []}


def _get_ray_document(doc_id: str) -> Dict[str, Any]:
    index_path = Path("/Users/raybayly/Development/Ray/mcp/data/indices/knowledge_index.json")
    if not index_path.is_file():
        return {"success": False, "error": "Ray knowledge index file not found."}
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw_docs = data.get("documents", [])
        documents = raw_docs.values() if isinstance(raw_docs, dict) else raw_docs
        for doc in documents:
            if doc.get("id") == doc_id or doc.get("relative_path") == doc_id:
                return {"success": True, "document": doc}
        return {"success": False, "error": f"Document '{doc_id}' not found."}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _get_session_memory(key: str) -> Dict[str, Any]:
    p = Path.cwd() / ".hath0r" / "cache" / "session_memory.json"
    if p.is_file():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {"key": key, "value": data.get(key), "exists": key in data}
        except Exception as exc:
            return {"key": key, "value": None, "error": str(exc)}
    return {"key": key, "value": None, "exists": False}


def _set_session_memory(key: str, value: Any, ttl_seconds: Optional[int] = None) -> Dict[str, Any]:
    p = Path.cwd() / ".hath0r" / "cache" / "session_memory.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {}
    if p.is_file():
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    data[key] = value
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return {"success": True, "key": key, "value": value}
    except Exception as exc:
        return {"success": False, "key": key, "error": str(exc)}


def _list_runbooks() -> Dict[str, Any]:
    kb_dir = Path("/Users/raybayly/Development/OpenSource/.hath0r/knowledgebase/canonical")
    runbooks = []
    for sub in ["runbooks", "playbooks", "procedures"]:
        d = kb_dir / sub
        if d.is_dir():
            for f in d.glob("*.md"):
                runbooks.append({"type": sub, "name": f.stem, "path": str(f)})
    return {"success": True, "count": len(runbooks), "runbooks": runbooks}


def _get_runbook_prompt(runbook_name: str, variables: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    kb_dir = Path("/Users/raybayly/Development/OpenSource/.hath0r/knowledgebase/canonical")
    target = None
    for sub in ["runbooks", "playbooks", "procedures"]:
        cand = kb_dir / sub / f"{runbook_name}.md"
        if cand.is_file():
            target = cand
            break
        for f in (kb_dir / sub).glob("*.md"):
            if runbook_name.lower() in f.stem.lower():
                target = f
                break
        if target:
            break

    if not target or not target.is_file():
        return {"success": False, "error": f"Runbook '{runbook_name}' not found."}

    content = target.read_text(encoding="utf-8")
    if variables:
        for k, v in variables.items():
            content = content.replace(f"${{{k}}}", str(v)).replace(f"${k}", str(v))
    return {"success": True, "runbook_path": str(target), "content": content}


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
        design = bot.generate_matrix(array_type=array, factors=factor_list)

        res: Dict[str, Any] = {
            "design": design,
        }

        if snr_values:
            snr = bot.calculate_snr(snr_values, criterion=criterion)
            res["snr"] = {
                "values": snr_values,
                "criterion": criterion,
                "snr_db": snr,
            }

        if loss_k is not None and target_m is not None and measured_y is not None:
            loss = bot.calculate_loss(measured_y=measured_y, target_m=target_m, sensitivity_k=loss_k)
            res["quality_loss"] = loss

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

        bot = TokenizerTaxBot()
        precision_bytes = 2 if precision in ("fp16", "bf16") else 4
        return bot.audit(text, vocab_size=vocab_size, hidden_dim=hidden_dim, precision_bytes=precision_bytes)

    @mcp.tool()
    def hath0r_finops_tokens_list(
        user: Optional[str] = None,
        agent: Optional[str] = None,
        session_id: Optional[str] = None,
        tier: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """Query prompt and completion token usage ledger records filtered by user, agent, session, tier, or model.

        Args:
            user: Filter by user name.
            agent: Filter by agent name.
            session_id: Filter by session ID.
            tier: Filter by model tier ('LIGHT', 'STANDARD', 'REASONING').
            model: Filter by model name.
            limit: Maximum number of records to return (1-200).
        """
        from hath0r_cli.bots.token_telemetry_bot import TokenTelemetryCLIBot

        bot = TokenTelemetryCLIBot()
        records = bot.list_records(
            user_id=user,
            agent_id=agent,
            session_id=session_id,
            tier=tier,
            model=model,
            limit=limit,
        )
        return {"records": records}

    @mcp.tool()
    def hath0r_finops_tokens_histogram(
        bin_field: str = "prompt_tokens",
        bins: int = 10,
        user: Optional[str] = None,
        agent: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate statistical metrics (p50, p90, p95, p99, mean, std dev) and ASCII histogram for token telemetry.

        Args:
            bin_field: Metric field to bin ('prompt_tokens', 'completion_tokens', 'prompt_chars', 'completion_chars', 'latency_ms').
            bins: Number of histogram bins (default 10).
            user: Optional user filter.
            agent: Optional agent filter.
            session_id: Optional session filter.
        """
        from hath0r_cli.bots.token_telemetry_bot import TokenTelemetryCLIBot

        bot = TokenTelemetryCLIBot()
        return bot.histogram(
            metric=bin_field,
            bins_count=bins,
            user_id=user,
            agent_id=agent,
            session_id=session_id,
        )

    @mcp.tool()
    def hath0r_finops_token_check(
        user_id: str = "raybayly",
        days: int = 90,
    ) -> Dict[str, Any]:
        """Execute the complete 'token check' workflow returning 90-day FinOps usage, histogram, and markdown report.

        Args:
            user_id: Target user profile identifier (default 'raybayly').
            days: Trailing window in days (default 90).
        """
        from hath0r_cli.bots.token_check_bot import TokenCheckWorkflowBot

        bot = TokenCheckWorkflowBot()
        return bot.run_token_check(user_id=user_id, days=days)

    @mcp.tool()
    def hath0r_agentgraph_status() -> Dict[str, Any]:
        """Inspect unified AgentGraph node, edge, plane distributions, and graph health status."""
        from hath0r_cli.bots.agentgraph_bot import AgentGraphBot

        bot = AgentGraphBot()
        return bot.get_status()

    @mcp.tool()
    def hath0r_agentgraph_query(
        topic: str,
        top_k: int = 5,
        plane: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Query AgentGraph rules, contracts, roles, and knowledge nodes matching a topic string.

        Args:
            topic: Topic or keyword string to search across AgentGraph nodes.
            top_k: Number of top results to return.
            plane: Optional plane filter ('knowledge', 'rules', 'context', 'memory').
        """
        from hath0r_cli.bots.agentgraph_bot import AgentGraphBot

        bot = AgentGraphBot()
        return bot.query(query_str=topic, top_k=top_k, plane=plane)

    @mcp.tool()
    def hath0r_agentgraph_route(
        role: str,
        tool: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate AgentGraph deterministic role RBAC policies and tool permissions before execution.

        Args:
            role: Agent role name (e.g. 'developer', 'reviewer', 'bot').
            tool: Optional tool name to check permissions against.
        """
        from hath0r_cli.bots.agentgraph_bot import AgentGraphBot

        bot = AgentGraphBot()
        return bot.route(role=role, tool=tool)

    @mcp.tool()
    def hath0r_voice_speak(
        text: str,
        voice: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesize and speak feedback text using platform speech synthesis engines.

        Args:
            text: Message text to convert to spoken speech output.
            voice: Optional voice name or voice profile.
        """
        from hath0r_cli.bots.voice_converse import VoiceSynthesizerBot

        bot = VoiceSynthesizerBot()
        return bot.speak(text=text, voice_name=voice)

    @mcp.tool()
    def hath0r_voice_listen(
        prompt: Optional[str] = None,
        simulated_transcript: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Capture or simulate a spoken utterance input turn from the user.

        Args:
            prompt: Optional verbal prompt spoken before listening.
            simulated_transcript: Optional transcript text for non-interactive speech simulation.
        """
        from hath0r_cli.bots.voice_converse import SpeechListenerBot, VoiceSynthesizerBot

        if prompt:
            VoiceSynthesizerBot().speak(prompt)
        bot = SpeechListenerBot()
        return bot.listen(simulated_transcript=simulated_transcript)

    @mcp.tool()
    def hath0r_ray_search(
        query: str,
        source: Optional[str] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        """Search across Ray's indexed personal knowledge store (author, career, documents, projects, persona).

        Args:
            query: Keywords or conceptual search query.
            source: Optional category filter ('author', 'career', 'documents', 'projects', 'persona').
            limit: Maximum documents to return.
        """
        return _search_ray_index(query=query, source=source, limit=limit)

    @mcp.tool()
    def hath0r_ray_get_document(
        doc_id: str,
    ) -> Dict[str, Any]:
        """Retrieve full content and metadata of a document by doc_id from Ray's indexed knowledge store.

        Args:
            doc_id: Document identifier (e.g. 'career:resume.md').
        """
        return _get_ray_document(doc_id=doc_id)

    @mcp.tool()
    def hath0r_session_get(
        key: str,
    ) -> Dict[str, Any]:
        """Retrieve a session variable or working memory key from local KV memory or Redis storage.

        Args:
            key: Key name to retrieve.
        """
        return _get_session_memory(key=key)

    @mcp.tool()
    def hath0r_session_set(
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Store a session variable or working memory key/value into local KV memory or Redis storage.

        Args:
            key: Memory key name.
            value: Value or JSON structure to store.
            ttl_seconds: Optional time-to-live expiration in seconds.
        """
        return _set_session_memory(key=key, value=value, ttl_seconds=ttl_seconds)

    @mcp.tool()
    def hath0r_runbook_list() -> Dict[str, Any]:
        """List all available runbooks, playbooks, and procedures in the Hath0r knowledgebase."""
        return _list_runbooks()

    @mcp.tool()
    def hath0r_runbook_get_prompt(
        runbook_name: str,
        variables: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Retrieve a prompt template or runbook procedure with variable substitution.

        Args:
            runbook_name: Name or filename slug of the target runbook/playbook.
            variables: Optional key-value substitutions for ${variable} placeholders.
        """
        return _get_runbook_prompt(runbook_name=runbook_name, variables=variables)

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
            val = json.loads(res.stdout)
            return val if isinstance(val, dict) else {"result": val}
        except Exception:
            return {"raw_output": res.stdout, "error": res.stderr}

    @mcp.tool()
    def hath0r_design_status() -> Dict[str, Any]:
        """Check status and connectivity of Paper.design MCP integration."""
        from hath0r_cli.bots.paper_design_bot import PaperDesignBot

        bot = PaperDesignBot()
        return bot.check_connection().to_dict()

    @mcp.tool()
    def hath0r_design_to_code(
        design_content: str,
        component_name: str = "WebSection",
        framework: str = "react_tailwind",
    ) -> Dict[str, Any]:
        """Synthesize React + Tailwind CSS component code from Paper canvas selection or HTML.

        Args:
            design_content: HTML layout or raw design content from Paper canvas.
            component_name: Name of the React component to synthesize.
            framework: Target UI framework ('react_tailwind' or 'html_css').
        """
        from hath0r_cli.bots.paper_design_bot import PaperDesignBot

        bot = PaperDesignBot()
        return bot.design_to_code(raw_design=design_content, component_name=component_name, framework=framework)

    return mcp

