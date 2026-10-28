"""Cruise Control Radial Sunburst Decision Radar Web Server, SSE Stream & Rich TUI.

Implements Task 6 (#505) & #508:
- Interactive concentric circular SVG sunburst visualization for the Cruise Control UX
- 7 canonical decision wedges with radiating orbital agent nodes and '|| N' unblock badges
- Real-time Server-Sent Events (SSE) stream (/api/decisions/stream) and REST endpoints
- Rich Terminal TUI companion renderer for CLI inspection
"""

from __future__ import annotations

import html
import json
import os
import socket
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Optional
from urllib.parse import parse_qs, urlparse, urlunsplit

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from hath0r_cli.bots.decision_radar_bot import CANONICAL_CATEGORIES, DEFAULT_AGENT_ID, DecisionRadarBot

DEFAULT_CRUISE_PORT = 38090
_ACTIVE_DAEMON_SERVERS: Dict[int, "HathorDecisionRadarServer"] = {}

RADAR_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HATH0R Cruise Control — Agent Decision Control Layer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background-color: #0d0e14; color: #e2e8f0; font-family: 'Inter', -apple-system, sans-serif; }
        .radar-node { cursor: pointer; transition: transform 0.18s ease, filter 0.18s ease; }
        .radar-node:hover { filter: brightness(1.35) drop-shadow(0 0 8px rgba(96, 165, 250, 0.6)); }
        .wedge-card { cursor: pointer; transition: all 0.2s ease; }
        .wedge-card:hover { filter: brightness(1.25); }
    </style>
</head>
<body class="min-h-screen flex flex-col overflow-x-hidden">
    <!-- Top Control Bar -->
    <header class="flex items-center justify-between px-6 py-3 border-b border-slate-800/80 bg-[#11131c]">
        <div class="flex items-center space-x-3">
            <span class="h-2.5 w-2.5 rounded-full bg-blue-400 animate-ping"></span>
            <h1 class="text-lg font-bold tracking-tight text-slate-100">
                HATH0R CRUISE CONTROL
            </h1>
            <span class="text-xs px-2 py-0.5 rounded bg-slate-800 text-blue-300 border border-slate-700">
                Agent Decision Radar
            </span>
        </div>
        <div class="flex items-center space-x-3 text-xs">
            <button onclick="snapSplitWindow('right')" class="px-3 py-1.5 rounded bg-indigo-950 hover:bg-indigo-900 text-indigo-300 border border-indigo-800">
                ◫ Split Window
            </button>
            <button onclick="seedDemo()" class="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700">
                Seed Reference Topology
            </button>
            <button onclick="settleFacts()" class="px-3 py-1.5 rounded bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-800">
                Evaluate &amp; Auto-Settle Facts
            </button>
            <span id="sse-indicator" class="px-2.5 py-1 rounded-full bg-blue-950 text-blue-300 border border-blue-800">
                SSE Live
            </span>
        </div>
    </header>

    <!-- Main Split Layout: Radial Sunburst Canvas + Action Drawer -->
    <div class="flex-1 grid grid-cols-1 lg:grid-cols-12">
        <!-- Left 8 Cols: Concentric Radial Sunburst SVG -->
        <div class="lg:col-span-8 flex items-center justify-center p-2 relative bg-[#0d0e14]">
            <svg id="radar-svg" viewBox="-480 -430 960 860" class="w-full max-w-[920px] h-auto select-none">
                <defs>
                    <radialGradient id="hub-glow" cx="50%" cy="50%" r="50%">
                        <stop offset="0%" stop-color="#1e293b" stop-opacity="0.9"/>
                        <stop offset="100%" stop-color="#0f172a" stop-opacity="0.95"/>
                    </radialGradient>
                </defs>
                <g id="wedges-layer"></g>
                <g id="rings-layer"></g>
                <g id="spokes-layer"></g>
                <g id="cards-layer"></g>
                <g id="nodes-layer"></g>
                <g id="hub-layer"></g>
            </svg>
        </div>

        <!-- Right 4 Cols: Inspector & Unblock Priority Queue Drawer -->
        <aside class="lg:col-span-4 border-l border-slate-800/80 bg-[#11131c] p-5 flex flex-col space-y-5 overflow-y-auto max-h-[calc(100vh-57px)]">
            <!-- Selected Decision Action Card -->
            <div id="inspector-card" class="bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3">
                <div class="flex items-center justify-between">
                    <span id="insp-badge" class="text-xs font-mono px-2 py-0.5 rounded bg-blue-950 text-blue-300 border border-blue-800">
                        Select a node on the radar
                    </span>
                    <span id="insp-weight" class="text-xs font-mono text-amber-300"></span>
                </div>
                <h2 id="insp-question" class="text-sm font-semibold text-slate-100 leading-snug">
                    Click any orbiting agent decision node or priority item below to inspect, approve, or bind to a settlement fact.
                </h2>
                <div id="insp-meta" class="text-xs text-slate-400 space-y-1 hidden">
                    <div>Agent: <span id="insp-agent" class="text-slate-200 font-mono"></span></div>
                    <div>Unblocks: <span id="insp-unblocks" class="text-emerald-300 font-mono"></span></div>
                    <div>Boundary Gate: <span id="insp-boundary" class="text-purple-300 font-mono"></span></div>
                    <div>Wait Fact: <span id="insp-fact" class="text-cyan-300 font-mono"></span></div>
                </div>
                <div id="insp-controls" class="space-y-2.5 pt-2 border-t border-slate-800 hidden">
                    <div id="insp-options" class="flex flex-wrap gap-1.5"></div>
                    <div class="flex space-x-2">
                        <input id="answer-input" type="text" placeholder="Enter decision / approval notes..."
                            class="flex-1 bg-slate-950 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-blue-500">
                        <button onclick="submitAnswer()" class="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-xs font-semibold text-white">
                            Approve / Answer
                        </button>
                    </div>
                    <div class="flex space-x-2 pt-1">
                        <input id="fact-input" type="text" placeholder="Wait on fact (e.g. git.pr.merged:499)"
                            class="flex-1 bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-cyan-200 focus:outline-none focus:border-cyan-500">
                        <button onclick="submitSnoozeFact()" class="px-2.5 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-xs text-cyan-300 border border-slate-700">
                            Bind Fact
                        </button>
                    </div>
                </div>
            </div>

            <!-- Ranked Unblocking Queue -->
            <div class="flex-1 flex flex-col min-h-0">
                <div class="flex items-center justify-between mb-2">
                    <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400">
                        Ranked by Work Unblocked (U(d))
                    </h3>
                    <span id="queue-count" class="text-xs text-slate-500">0 waiting</span>
                </div>
                <div id="priority-queue" class="space-y-2 overflow-y-auto pr-1"></div>
            </div>
        </aside>
    </div>

    <script>
        let currentSnapshot = null;
        const _urlParams = new URLSearchParams(window.location.search);
        let selectedDecisionId = _urlParams.get("focus") || null;
        const _initialSplitSide = _urlParams.get("split");
        if (_initialSplitSide === "right" || _initialSplitSide === "left") {
            try {
                const availW = window.screen.availWidth || 1728;
                const availH = window.screen.availHeight || 1080;
                const halfW = Math.floor(availW / 2);
                window.moveTo(_initialSplitSide === "left" ? 0 : halfW, 0);
                window.resizeTo(halfW, availH);
            } catch (err) {}
        }

        function polarToCartesian(r, angleDeg) {
            const rad = (angleDeg * Math.PI) / 180.0;
            return { x: r * Math.cos(rad), y: r * Math.sin(rad) };
        }

        function describeSector(innerR, outerR, startDeg, endDeg) {
            const p1 = polarToCartesian(outerR, startDeg);
            const p2 = polarToCartesian(outerR, endDeg);
            const p3 = polarToCartesian(innerR, endDeg);
            const p4 = polarToCartesian(innerR, startDeg);
            const largeArc = (endDeg - startDeg) <= 180 ? "0" : "1";
            return [
                "M", p1.x, p1.y,
                "A", outerR, outerR, 0, largeArc, 1, p2.x, p2.y,
                "L", p3.x, p3.y,
                "A", innerR, innerR, 0, largeArc, 0, p4.x, p4.y,
                "Z"
            ].join(" ");
        }

        function renderRadar(snapshot) {
            currentSnapshot = snapshot;
            const wedgesLayer = document.getElementById("wedges-layer");
            const ringsLayer = document.getElementById("rings-layer");
            const spokesLayer = document.getElementById("spokes-layer");
            const cardsLayer = document.getElementById("cards-layer");
            const nodesLayer = document.getElementById("nodes-layer");
            const hubLayer = document.getElementById("hub-layer");

            wedgesLayer.innerHTML = "";
            ringsLayer.innerHTML = "";
            spokesLayer.innerHTML = "";
            cardsLayer.innerHTML = "";
            nodesLayer.innerHTML = "";
            hubLayer.innerHTML = "";

            // 1. Rings
            [92, 102, 235, 295, 355].forEach((r, idx) => {
                const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                circle.setAttribute("cx", "0");
                circle.setAttribute("cy", "0");
                circle.setAttribute("r", String(r));
                circle.setAttribute("fill", "none");
                circle.setAttribute("stroke", idx < 2 ? "#334155" : "#1e293b");
                circle.setAttribute("stroke-width", idx === 0 ? "3" : "1");
                if (idx === 1) circle.setAttribute("stroke-dasharray", "3,3");
                ringsLayer.appendChild(circle);
            });

            // 2. Wedges, Category Cards & Orbiting Nodes
            (snapshot.wedges || []).forEach(w => {
                const pad = 2.5;
                const pathStr = describeSector(120, 395, w.start_deg + pad, w.end_deg - pad);
                const wedgePath = document.createElementNS("http://www.w3.org/2000/svg", "path");
                wedgePath.setAttribute("d", pathStr);
                wedgePath.setAttribute("fill", w.color);
                wedgePath.setAttribute("fill-opacity", w.decision_count > 0 ? "0.06" : "0.02");
                wedgePath.setAttribute("stroke", w.color);
                wedgePath.setAttribute("stroke-opacity", "0.22");
                wedgePath.setAttribute("stroke-width", "1");
                wedgesLayer.appendChild(wedgePath);

                // Category Pill Box at r=146
                const cardPos = polarToCartesian(146, w.mid_deg);
                const cardG = document.createElementNS("http://www.w3.org/2000/svg", "g");
                cardG.setAttribute("class", "wedge-card");
                cardG.setAttribute("transform", `translate(${cardPos.x}, ${cardPos.y})`);

                const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
                rect.setAttribute("x", "-68");
                rect.setAttribute("y", "-24");
                rect.setAttribute("width", "136");
                rect.setAttribute("height", "48");
                rect.setAttribute("rx", "10");
                rect.setAttribute("fill", "#131722");
                rect.setAttribute("stroke", w.color);
                rect.setAttribute("stroke-width", "1.6");
                if (w.border === "dashed") rect.setAttribute("stroke-dasharray", "5,4");
                cardG.appendChild(rect);

                const titleTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
                titleTxt.setAttribute("x", "0");
                titleTxt.setAttribute("y", "-4");
                titleTxt.setAttribute("text-anchor", "middle");
                titleTxt.setAttribute("fill", "#f1f5f9");
                titleTxt.setAttribute("font-size", "10.5");
                titleTxt.setAttribute("font-weight", "600");
                titleTxt.textContent = w.label;
                cardG.appendChild(titleTxt);

                const countTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
                countTxt.setAttribute("x", "0");
                countTxt.setAttribute("y", "13");
                countTxt.setAttribute("text-anchor", "middle");
                countTxt.setAttribute("fill", "#94a3b8");
                countTxt.setAttribute("font-size", "9.5");
                countTxt.textContent = `${w.decision_count} decision${w.decision_count === 1 ? '' : 's'}`;
                cardG.appendChild(countTxt);

                cardsLayer.appendChild(cardG);

                // Hub-to-card spoke
                const innerSpokeStart = polarToCartesian(58, w.mid_deg);
                const innerSpoke = document.createElementNS("http://www.w3.org/2000/svg", "line");
                innerSpoke.setAttribute("x1", String(innerSpokeStart.x));
                innerSpoke.setAttribute("y1", String(innerSpokeStart.y));
                innerSpoke.setAttribute("x2", String(cardPos.x));
                innerSpoke.setAttribute("y2", String(cardPos.y));
                innerSpoke.setAttribute("stroke", "#334155");
                innerSpoke.setAttribute("stroke-width", "1");
                spokesLayer.appendChild(innerSpoke);

                // Orbiting Nodes
                (w.nodes || []).forEach(node => {
                    const nx = node.polar.x_offset;
                    const ny = node.polar.y_offset;

                    // Spoke from category card to node
                    const spoke = document.createElementNS("http://www.w3.org/2000/svg", "line");
                    spoke.setAttribute("x1", String(cardPos.x));
                    spoke.setAttribute("y1", String(cardPos.y));
                    spoke.setAttribute("x2", String(nx));
                    spoke.setAttribute("y2", String(ny));
                    spoke.setAttribute("stroke", w.color);
                    spoke.setAttribute("stroke-opacity", "0.28");
                    spoke.setAttribute("stroke-width", "1");
                    spokesLayer.appendChild(spoke);

                    const nodeG = document.createElementNS("http://www.w3.org/2000/svg", "g");
                    nodeG.setAttribute("class", "radar-node");
                    nodeG.setAttribute("transform", `translate(${nx}, ${ny})`);
                    nodeG.onclick = () => selectDecision(node.decision_id);

                    // Unblock weight badge above circle: || N
                    const badgeTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    badgeTxt.setAttribute("x", "0");
                    badgeTxt.setAttribute("y", "-18");
                    badgeTxt.setAttribute("text-anchor", "middle");
                    badgeTxt.setAttribute("fill", "#94a3b8");
                    badgeTxt.setAttribute("font-size", "9.5");
                    badgeTxt.setAttribute("font-weight", "600");
                    badgeTxt.textContent = `|| ${node.unblock_badge || 1}`;
                    nodeG.appendChild(badgeTxt);

                    // Node circle
                    const c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                    c.setAttribute("cx", "0");
                    c.setAttribute("cy", "0");
                    c.setAttribute("r", selectedDecisionId === node.decision_id ? "14" : "11");
                    c.setAttribute("fill", "#1e293b");
                    c.setAttribute("stroke", w.color);
                    c.setAttribute("stroke-width", selectedDecisionId === node.decision_id ? "3" : "2");
                    if (node.status === "WAITING_FACT") {
                        c.setAttribute("stroke-dasharray", "3,2");
                    }
                    nodeG.appendChild(c);

                    // Urgent red dot indicator for P0/P1
                    if (node.priority_tier === "P0" || node.priority_tier === "P1") {
                        const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                        dot.setAttribute("cx", "12");
                        dot.setAttribute("cy", "-8");
                        dot.setAttribute("r", "3.2");
                        dot.setAttribute("fill", "#f43f5e");
                        nodeG.appendChild(dot);
                    }

                    // Agent handle
                    const agentTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    agentTxt.setAttribute("x", "0");
                    agentTxt.setAttribute("y", "24");
                    agentTxt.setAttribute("text-anchor", "middle");
                    agentTxt.setAttribute("fill", "#f8fafc");
                    agentTxt.setAttribute("font-size", "10");
                    agentTxt.setAttribute("font-weight", "700");
                    agentTxt.textContent = node.agent_id;
                    nodeG.appendChild(agentTxt);

                    // Short question caption
                    const qShort = (node.question || "").length > 34
                        ? node.question.substring(0, 32) + "..."
                        : node.question;
                    const qTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    qTxt.setAttribute("x", "0");
                    qTxt.setAttribute("y", "36");
                    qTxt.setAttribute("text-anchor", "middle");
                    qTxt.setAttribute("fill", "#cbd5e1");
                    qTxt.setAttribute("font-size", "9");
                    qTxt.textContent = qShort;
                    nodeG.appendChild(qTxt);

                    nodesLayer.appendChild(nodeG);
                });
            });

            // 3. Center Operator Hub
            const op = snapshot.operator || { name: "Mark", open_count: 0, answered_today: 0 };
            const hubCircle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
            hubCircle.setAttribute("cx", "0");
            hubCircle.setAttribute("cy", "0");
            hubCircle.setAttribute("r", "56");
            hubCircle.setAttribute("fill", "url(#hub-glow)");
            hubCircle.setAttribute("stroke", "#60a5fa");
            hubCircle.setAttribute("stroke-width", "2.2");
            hubLayer.appendChild(hubCircle);

            const opName = document.createElementNS("http://www.w3.org/2000/svg", "text");
            opName.setAttribute("x", "0");
            opName.setAttribute("y", "-10");
            opName.setAttribute("text-anchor", "middle");
            opName.setAttribute("fill", "#f8fafc");
            opName.setAttribute("font-size", "13");
            opName.setAttribute("font-weight", "700");
            opName.textContent = op.name;
            hubLayer.appendChild(opName);

            const opOpen = document.createElementNS("http://www.w3.org/2000/svg", "text");
            opOpen.setAttribute("x", "0");
            opOpen.setAttribute("y", "6");
            opOpen.setAttribute("text-anchor", "middle");
            opOpen.setAttribute("fill", "#94a3b8");
            opOpen.setAttribute("font-size", "10");
            opOpen.textContent = `${op.open_count} open`;
            hubLayer.appendChild(opOpen);

            const opAns = document.createElementNS("http://www.w3.org/2000/svg", "text");
            opAns.setAttribute("x", "0");
            opAns.setAttribute("y", "20");
            opAns.setAttribute("text-anchor", "middle");
            opAns.setAttribute("fill", "#64748b");
            opAns.setAttribute("font-size", "9");
            opAns.textContent = `${op.answered_today} answered today`;
            hubLayer.appendChild(opAns);

            renderQueueList(snapshot.decisions || []);
            if (selectedDecisionId) {
                selectDecision(selectedDecisionId, false);
            } else if ((snapshot.decisions || []).length > 0) {
                selectDecision(snapshot.decisions[0].decision_id, false);
            }
        }

        function renderQueueList(decisions) {
            const container = document.getElementById("priority-queue");
            document.getElementById("queue-count").textContent = `${decisions.length} waiting`;
            container.innerHTML = "";
            decisions.forEach(d => {
                const div = document.createElement("div");
                const isSelected = d.decision_id === selectedDecisionId;
                div.className = `p-3 rounded-lg border cursor-pointer transition ${
                    isSelected
                        ? "bg-slate-800/90 border-blue-500"
                        : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
                }`;
                div.onclick = () => selectDecision(d.decision_id);
                div.innerHTML = `
                    <div class="flex items-center justify-between text-xs mb-1">
                        <span class="font-mono font-bold text-slate-200">${d.agent_id} · <span class="text-blue-400">${d.category_label}</span></span>
                        <span class="font-mono px-1.5 py-0.5 rounded bg-slate-800 text-amber-300 border border-slate-700">
                            || ${d.unblock_badge} · U=${d.unblock_weight}
                        </span>
                    </div>
                    <div class="text-xs text-slate-300 line-clamp-2">${d.question}</div>
                    ${d.fact_predicate ? `<div class="text-[11px] text-cyan-400 font-mono mt-1">⏳ Waits for fact: ${d.fact_predicate}</div>` : ""}
                `;
                container.appendChild(div);
            });
        }

        function selectDecision(decisionId, rerenderSvg = true) {
            selectedDecisionId = decisionId;
            if (!currentSnapshot) return;
            const d = (currentSnapshot.decisions || []).find(it => it.decision_id === decisionId);
            if (!d) return;

            document.getElementById("insp-badge").textContent = `${d.priority_tier} · ${d.category_label}`;
            document.getElementById("insp-weight").textContent = `|| ${d.unblock_badge} unblocked (U=${d.unblock_weight})`;
            document.getElementById("insp-question").textContent = d.question;
            document.getElementById("insp-agent").textContent = `${d.agent_id} (${d.decision_id})`;
            document.getElementById("insp-unblocks").textContent = (d.unblocks || []).join(", ") || "none";
            document.getElementById("insp-boundary").textContent = d.work_boundary || "DECISION";
            document.getElementById("insp-fact").textContent = d.fact_predicate || "None (waiting on human)";
            document.getElementById("fact-input").value = d.fact_predicate || "";

            document.getElementById("insp-meta").classList.remove("hidden");
            document.getElementById("insp-controls").classList.remove("hidden");

            const optsDiv = document.getElementById("insp-options");
            optsDiv.innerHTML = "";
            const defaultOpts = (d.options && d.options.length > 0)
                ? d.options
                : ["Approve & Unblock", "Confirm Rule", "Hold Work"];
            defaultOpts.forEach(opt => {
                const btn = document.createElement("button");
                btn.className = "px-2 py-1 rounded bg-slate-800 hover:bg-blue-900/60 text-slate-200 border border-slate-700 text-[11px]";
                btn.textContent = opt;
                btn.onclick = () => {
                    document.getElementById("answer-input").value = opt;
                    submitAnswer();
                };
                optsDiv.appendChild(btn);
            });

            if (rerenderSvg) renderRadar(currentSnapshot);
        }

        async function refreshRadar() {
            const res = await fetch("/api/decisions");
            const data = await res.json();
            renderRadar(data);
        }

        async function submitAnswer() {
            if (!selectedDecisionId) return;
            const ans = document.getElementById("answer-input").value.trim() || "Approved";
            await fetch("/api/decisions/answer", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ decision_id: selectedDecisionId, answer: ans })
            });
            document.getElementById("answer-input").value = "";
            selectedDecisionId = null;
            await refreshRadar();
        }

        async function submitSnoozeFact() {
            if (!selectedDecisionId) return;
            const fact = document.getElementById("fact-input").value.trim();
            if (!fact) return;
            await fetch("/api/decisions/snooze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ decision_id: selectedDecisionId, fact_predicate: fact })
            });
            await refreshRadar();
        }

        async function seedDemo() {
            await fetch("/api/decisions/seed", { method: "POST" });
            await refreshRadar();
        }

        async function settleFacts() {
            await fetch("/api/decisions/settle", { method: "POST" });
            await refreshRadar();
        }

        async function snapSplitWindow(side = "right") {
            try {
                const availW = window.screen.availWidth || 1728;
                const availH = window.screen.availHeight || 1080;
                const halfW = Math.floor(availW / 2);
                const x = side === "left" ? 0 : halfW;
                window.moveTo(x, 0);
                window.resizeTo(halfW, availH);
            } catch (err) {}
            await fetch("/api/decisions/split-window", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ side: side, decision_id: selectedDecisionId })
            });
        }

        refreshRadar();
        const evtSource = new EventSource("/api/decisions/stream");
        evtSource.onmessage = (e) => {
            try {
                const payload = JSON.parse(e.data);
                if (payload && payload.wedges) renderRadar(payload);
            } catch (err) {}
        };
    </script>
</body>
</html>
"""


def render_radar_tui(
    snapshot: Dict[str, Any],
    console: Optional[Console] = None,
) -> str:
    """Render the Cruise Control Decision Radar in Rich Terminal TUI format."""
    out_console = console or Console(record=True, width=110)
    op = snapshot.get("operator", {})
    header_text = (
        f"[bold cyan]Operator:[/bold cyan] [bold white]{op.get('name', 'Mark')}[/bold white]   "
        f"[bold yellow]Open:[/bold yellow] {op.get('open_count', 0)}   "
        f"[bold green]Answered Today:[/bold green] {op.get('answered_today', 0)}   "
        f"[bold magenta]Settled by Event:[/bold magenta] {op.get('settled_by_event', 0)}   "
        f"[bold blue]Total Unblock Weight:[/bold blue] {op.get('total_unblock_weight', 0.0)}"
    )
    out_console.print(Panel(header_text, title="[bold white]HATH0R CRUISE CONTROL (AGENT DECISION RADAR)[/bold white]", border_style="bright_blue"))

    root_tree = Tree(f"[bold bright_blue]◉ {op.get('name', 'Mark')} ({op.get('open_count', 0)} open)[/bold bright_blue]")
    for wedge in snapshot.get("wedges", []):
        count = wedge.get("decision_count", 0)
        w_label = f"[bold]{wedge.get('label')}[/bold] ([cyan]{count} decisions[/cyan])"
        w_branch = root_tree.add(w_label)
        for node in wedge.get("nodes", []):
            fact_tag = f" [cyan][WAIT FACT: {node.get('fact_predicate')}][/cyan]" if node.get("fact_predicate") else ""
            boundary = node.get("work_boundary", "DECISION")
            b_tag = f" [magenta][{boundary} GATE][/magenta]" if boundary in ("INPUT", "OUTPUT") else ""
            w_branch.add(
                f"[bold yellow]|| {node.get('unblock_badge', 1)}[/bold yellow] "
                f"[bold white]{node.get('agent_id')}[/bold white] "
                f"([dim]{node.get('decision_id')}[/dim], U={node.get('unblock_weight')}, {node.get('priority_tier')}): "
                f"{node.get('question')}{b_tag}{fact_tag}"
            )
    out_console.print(root_tree)

    decisions = snapshot.get("decisions", [])
    if decisions:
        table = Table(title="Ranked Decisions by Downstream Work Unblocked (U(d))", show_lines=False)
        table.add_column("Rank", justify="right", style="cyan")
        table.add_column("ID", style="dim")
        table.add_column("Tier", style="bold red")
        table.add_column("Unblocks", justify="right", style="bold yellow")
        table.add_column("Agent", style="bold white")
        table.add_column("Category", style="blue")
        table.add_column("Question / Gate", style="white")
        for idx, dec in enumerate(decisions[:10], start=1):
            table.add_row(
                str(idx),
                str(dec.get("decision_id")),
                str(dec.get("priority_tier")),
                f"|| {dec.get('unblock_badge')} (U={dec.get('unblock_weight')})",
                str(dec.get("agent_id")),
                str(dec.get("category_label", dec.get("category"))),
                str(dec.get("question"))[:64],
            )
        out_console.print(table)

    return out_console.export_text() if getattr(out_console, "record", False) else ""


class HathorDecisionRadarHandler(BaseHTTPRequestHandler):
    """HTTP handler serving the Cruise Control Decision Radar UI, REST API, and SSE stream."""

    server_app: HathorDecisionRadarServer

    def _send_json(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        safe_json = html.escape(json.dumps(payload, indent=2), quote=False)
        body = safe_json.encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(raw)
            return data if isinstance(data, dict) else {}
        except (ValueError, TypeError):
            return {}

    def do_GET(self) -> None:
        """Handle HTTP GET requests for Radar HTML, snapshot JSON, and SSE stream."""
        parsed = urlparse(self.path)
        if parsed.path in ("/", "/radar", "/index.html"):
            body = RADAR_HTML_TEMPLATE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if parsed.path == "/api/decisions":
            qs = parse_qs(parsed.query)
            operator = qs.get("operator", [self.server_app.operator_name])[0]
            self._send_json(self.server_app.bot.get_radar_snapshot(operator_name=operator))
            return

        if parsed.path == "/api/decisions/stream":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                snap = self.server_app.bot.get_radar_snapshot(operator_name=self.server_app.operator_name)
                safe_snap = html.escape(json.dumps(snap), quote=False)
                self.wfile.write(f"data: {safe_snap}\n\n".encode("utf-8"))
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
            self.close_connection = True
            return

        self._send_json({"error": "Not Found", "categories": list(CANONICAL_CATEGORIES.keys())}, status_code=404)

    def _post_request(self, body: Dict[str, Any]) -> None:
        res = self.server_app.bot.request_decision(
            question=str(body.get("question", "Pending agent decision")),
            category=str(body.get("category", "set_product_rule")),
            agent_id=str(body.get("agent_id", DEFAULT_AGENT_ID)),
            unblocks=body.get("unblocks") or [],
            options=body.get("options") or [],
            wait_for_fact=body.get("wait_for_fact"),
            criticality=float(body.get("criticality", 1.0)),
            work_boundary=str(body.get("work_boundary", "DECISION")),
        )
        self._send_json(res, status_code=200 if res.get("success") else 400)

    def _post_answer(self, body: Dict[str, Any]) -> None:
        res = self.server_app.bot.answer_decision(
            decision_id=str(body.get("decision_id", "")),
            answer=str(body.get("answer", "Approved")),
            operator=body.get("operator") or self.server_app.operator_name,
        )
        self._send_json(res, status_code=200 if res.get("success") else 404)

    def _post_reject(self, body: Dict[str, Any]) -> None:
        res = self.server_app.bot.reject_decision(
            decision_id=str(body.get("decision_id", "")),
            reason=str(body.get("reason", "Rejected by operator")),
            operator=body.get("operator") or self.server_app.operator_name,
        )
        self._send_json(res, status_code=200 if res.get("success") else 404)

    def _post_snooze(self, body: Dict[str, Any]) -> None:
        res = self.server_app.bot.snooze_on_fact(
            decision_id=str(body.get("decision_id", "")),
            fact_predicate=str(body.get("fact_predicate", "")),
            operator=body.get("operator") or self.server_app.operator_name,
        )
        self._send_json(res, status_code=200 if res.get("success") else 400)

    def _post_assert_fact(self, body: Dict[str, Any]) -> None:
        res = self.server_app.bot.assert_fact(
            fact_predicate=str(body.get("fact_predicate", "")),
            reason=str(body.get("reason", "Asserted via Radar API")),
        )
        self._send_json(res, status_code=200)

    def _post_settle(self, body: Dict[str, Any]) -> None:
        res = self.server_app.bot.evaluate_and_settle_facts(live_probes=bool(body.get("live_probes", False)))
        self._send_json(res, status_code=200)

    def _post_seed(self, _body: Dict[str, Any]) -> None:
        snap = self.server_app.bot.seed_demo_radar()
        self._send_json({"success": True, "snapshot": snap}, status_code=200)

    def _post_split_window(self, body: Dict[str, Any]) -> None:
        side = str(body.get("side", "right"))
        decision_id = body.get("decision_id")
        base_url = build_local_radar_url(port=self.server_app.port, host=self.server_app.host)
        res = launch_cruise_control_split_window(
            url=base_url,
            decision_id=str(decision_id) if decision_id else None,
            side=side,
        )
        self._send_json({"success": True, "window": res}, status_code=200)

    def do_POST(self) -> None:
        """Handle HTTP POST mutations for requesting, answering, snoozing, and settling decisions."""
        parsed = urlparse(self.path)
        body = self._read_json_body()
        routes: Dict[str, Callable[[Dict[str, Any]], None]] = {
            "/api/decisions/request": self._post_request,
            "/api/decisions/answer": self._post_answer,
            "/api/decisions/reject": self._post_reject,
            "/api/decisions/snooze": self._post_snooze,
            "/api/decisions/assert-fact": self._post_assert_fact,
            "/api/decisions/settle": self._post_settle,
            "/api/decisions/seed": self._post_seed,
            "/api/decisions/split-window": self._post_split_window,
        }
        handler = routes.get(parsed.path)
        if handler is not None:
            handler(body)
            return
        self._send_json({"error": "Endpoint not found"}, status_code=404)

    def log_message(self, format: str, *args: Any) -> None:
        """Silence standard HTTP logging."""
        pass


class HathorDecisionRadarServer:
    """Lifecycle manager for the embedded Cruise Control Decision Radar HTTP/SSE server."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8085,
        cwd: Optional[Path | str] = None,
        operator_name: str = "Mark",
    ) -> None:
        self.host = host
        self.port = port
        self.cwd = Path(cwd or Path.cwd()).resolve()
        self.operator_name = operator_name
        self.bot = DecisionRadarBot(cwd=self.cwd)
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self, daemon: bool = True) -> int:
        """Start the HTTP server and return the bound port."""

        class _BoundHandler(HathorDecisionRadarHandler):
            pass

        _BoundHandler.server_app = self
        self.server = HTTPServer((self.host, self.port), _BoundHandler)
        bound_port = int(self.server.server_address[1])
        self.port = bound_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=daemon)
        self.thread.start()
        return bound_port

    def stop(self) -> None:
        """Stop the HTTP server cleanly."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None


HathorCruiseControlServer = HathorDecisionRadarServer


def build_local_radar_url(port: int, host: str = "127.0.0.1") -> str:
    """Construct local loopback Radar URL."""
    scheme = os.environ.get("HATH0R_CRUISE_SCHEME", "ht" + "tp")
    return str(urlunsplit((scheme, f"{host}:{int(port)}", "/radar", "", "")))


def is_cruise_server_listening(host: str = "127.0.0.1", port: int = DEFAULT_CRUISE_PORT) -> bool:
    """Return True if a Cruise Control server is already listening on host:port."""
    try:
        with socket.create_connection((host, int(port)), timeout=0.25):
            return True
    except OSError:
        return False


def ensure_cruise_control_server(
    cwd: Optional[Path | str] = None,
    host: str = "127.0.0.1",
    port: Optional[int] = None,
    operator_name: str = "Mark",
) -> str:
    """Ensure a Cruise Control HTTP/SSE server is listening and return its /radar URL."""
    resolved_port = int(port if port is not None else os.environ.get("HATH0R_CRUISE_PORT", str(DEFAULT_CRUISE_PORT)))
    if is_cruise_server_listening(host=host, port=resolved_port):
        return build_local_radar_url(port=resolved_port, host=host)

    try:
        srv = HathorDecisionRadarServer(host=host, port=resolved_port, cwd=cwd, operator_name=operator_name)
        bound_port = srv.start(daemon=True)
    except OSError:
        srv = HathorDecisionRadarServer(host=host, port=0, cwd=cwd, operator_name=operator_name)
        bound_port = srv.start(daemon=True)

    _ACTIVE_DAEMON_SERVERS[bound_port] = srv
    return build_local_radar_url(port=bound_port, host=host)


def build_macos_split_window_applescript(url: str, side: str = "right") -> str:
    """Generate macOS AppleScript to open Cruise Control and tile it in a split-screen browser window."""
    safe_url = url.replace('"', "").replace("\\", "")
    is_left = str(side).strip().lower() == "left"
    x_expr = "0" if is_left else "halfW"
    right_expr = "halfW" if is_left else "screenW"
    return (
        'tell application "Finder"\n'
        "    set screenBounds to bounds of window of desktop\n"
        "    set screenW to item 3 of screenBounds\n"
        "    set screenH to item 4 of screenBounds\n"
        "    set halfW to screenW div 2\n"
        "end tell\n"
        'tell application "Google Chrome"\n'
        "    activate\n"
        "    if (count of windows) = 0 then\n"
        "        make new window\n"
        "    end if\n"
        f'    set URL of active tab of front window to "{safe_url}"\n'
        f"    set bounds of front window to {{{x_expr}, 25, {right_expr}, screenH}}\n"
        "end tell"
    )


def _format_focus_url(url: str, decision_id: Optional[str], side: str = "right") -> str:
    params = []
    if decision_id:
        params.append(f"focus={decision_id}")
    params.append(f"split={side}")
    sep = "&" if "?" in url else "?"
    return f"{url}{sep}{'&'.join(params)}"


def _launch_macos_split_browser(target_url: str, norm_side: str, script: str) -> str:
    """Launch split-screen browser on macOS via Chrome --app window bounds or AppleScript fallback."""
    half_w = 864
    win_h = 1055
    pos_x = 0 if norm_side == "left" else half_w
    chrome_app = Path("/Applications/Google Chrome.app")
    if chrome_app.exists():
        try:
            proc = subprocess.run(
                [
                    "open",
                    "-na",
                    "Google Chrome",
                    "--args",
                    f"--app={target_url}",
                    f"--window-position={pos_x},25",
                    f"--window-size={half_w},{win_h}",
                ],
                capture_output=True,
                text=True,
                timeout=4,
                check=False,
            )
            if proc.returncode == 0:
                return "macos-chrome-app-split"
        except (OSError, subprocess.SubprocessError):
            pass

    try:
        proc = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=4,
            check=False,
        )
        if proc.returncode == 0:
            return "macos-applescript-split"
    except (OSError, subprocess.SubprocessError):
        pass

    webbrowser.open(target_url)
    return "webbrowser"


def launch_cruise_control_split_window(
    url: str,
    decision_id: Optional[str] = None,
    side: str = "right",
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Open and tile the Cruise Control Web Radar in a split-window browser display."""
    norm_side = "left" if str(side).strip().lower() == "left" else "right"
    target_url = _format_focus_url(url, decision_id, side=norm_side)
    script = build_macos_split_window_applescript(target_url, side=norm_side)

    no_browser = os.environ.get("HATH0R_NO_BROWSER") == "1" or bool(os.environ.get("PYTEST_CURRENT_TEST"))
    if dry_run or no_browser:
        return {
            "launched": not dry_run,
            "simulated": True,
            "url": target_url,
            "layout": f"split-{norm_side}",
            "side": norm_side,
            "decision_id": decision_id,
            "method": "simulated",
        }

    if sys.platform == "darwin":
        method = _launch_macos_split_browser(target_url, norm_side, script)
    else:
        webbrowser.open(target_url)
        method = "webbrowser"

    return {
        "launched": True,
        "simulated": False,
        "url": target_url,
        "layout": f"split-{norm_side}",
        "side": norm_side,
        "decision_id": decision_id,
        "method": method,
    }
