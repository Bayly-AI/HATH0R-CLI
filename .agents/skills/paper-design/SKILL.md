---
name: paper-design
description: Direct integration with Paper.design MCP server for website UI/UX design, bi-directional canvas-to-code synthesis, artboard staging, token extraction, and web accessibility audits. Activates when designing websites, syncing with Paper canvas, converting Paper artboards to React/Tailwind, or using Paper.design.
---

# Paper.design MCP Integration & Website Design SOP

This skill guides agents in designing websites using **Paper.design** through its Model Context Protocol (MCP) server, integrating visual web canvas layouts directly with production React 18, Vite, and Tailwind CSS.

---

## 1. Overview & Architecture

**Paper (paper.design)** is a web-standards native design tool that natively supports HTML, CSS, DOM layouts, and flexbox containers. Its built-in MCP server bridges AI agents and visual design canvases.

### MCP Endpoints & Transports
- **Local Daemon (HTTP/SSE)**: `http://127.0.0.1:29979/mcp` (active when Paper Desktop is running)
- **Local CLI (stdio)**: `~/.paper/bin/paper mcp`
- **Hath0r CLI Command Group**: `hath0r design`
- **Canonical Priority**: Configured in Hath0r MCP registry as `paper-design-mcp` (scope: `tools`, priority `4`).

### Core Paper MCP Tools
1. `paper:get_selection`: Inspects the currently active artboard, frame, or element on the open Paper canvas.
2. `paper:read_file`: Reads canvas files, linked styles, and artboard hierarchies.
3. `paper:create_artboard`: Programmatically creates new artboards/frames with specified dimensions and auto-layout settings.
4. `paper:write_html`: Injects, updates, or renders semantic HTML and CSS directly into target frames on the canvas.
5. `paper:update_style`: Adjusts style properties, color tokens, and layout constraints.

---

## 2. Standard Operating Procedures (SOP)

### Step 1: Connectivity & Readiness Check
Before attempting design operations, verify that the Paper Desktop MCP server is reachable:

```bash
hath0r design status
# or with JSON output
hath0r --output json design status
```

**Diagnostic States:**
- **`ONLINE`**: Paper Desktop background daemon is running on port 29979. All canvas tools are ready.
- **`CLI_AVAILABLE`**: Executable found at `~/.paper/bin/paper`. Stdio sessions can be established.
- **`OFFLINE`**: Neither daemon nor CLI found.
  - *Remediation*: Launch Paper Desktop app and open a project canvas, or install CLI via `claude plugin marketplace add paper-design/agent-plugins`.

---

### Step 2: Canvas Inspection
Inspect the user's active canvas selection or artboards:

```bash
hath0r design inspect
```

When connected, this returns:
- Target artboard ID & name (e.g., `Hero / Desktop`)
- Canvas dimensions (width × height)
- Element tree and DOM layout properties

---

### Step 3: Design-to-Code Synthesis
Synthesize modern, responsive, accessible React + Tailwind CSS components from the active Paper design or an HTML mockup:

```bash
hath0r design to-code --name HeroSection --framework react_tailwind --output src/app/components/HeroSection.tsx
```

**Synthesis Rules for Website Production:**
1. **Design System Consistency**:
   - Align with the project's color palette (e.g., electric blue `#38bdf8`, dark slate `#020617`, `#0f172a`).
   - Use standard typography scales and responsive spacing (`px-6 lg:px-8`, `py-24 sm:py-32`).
2. **Component Architecture**:
   - TypeScript interface for props (e.g., `HeroSectionProps`).
   - Defaults for all optional props.
   - Clean export statement (`export const HeroSection: React.FC<...>`).
3. **Accessibility (a11y)**:
   - Proper landmark tags (`<header>`, `<nav>`, `<main>`, `<section>`, `<footer>`).
   - All `<img>` tags must include meaningful `alt` descriptions.
   - All interactive controls (buttons, links) must have accessible labels and focus rings (`focus-visible:outline-2`).

---

### Step 4: Code-to-Canvas Staging (Pushing to Paper)
When prototyping a new website section in code and visualizing it on the Paper canvas:

```bash
hath0r design to-canvas --input-file src/app/components/HeroSection.tsx --name "Hero Section Artboard" --width 1440 --height 900
```

This formats the component into a clean preview container and dispatches the payload to `paper:write_html` and `paper:create_artboard`.

---

### Step 5: Design Token Synchronization
Extract color swatches, font hierarchies, and border radius tokens directly from CSS or canvas structures into Tailwind config:

```bash
hath0r design tokens src/styles/site.css
```

Outputs:
- `:root` CSS custom properties
- Tailwind `theme.extend` color palette

---

### Step 6: Layout & Accessibility Audit Gate
Run the automated quality gate before committing new website designs:

```bash
hath0r design audit src/index.html
```

Ensures:
- Accessibility score $\ge 80/100$
- No missing landmark tags
- No missing image alt texts
- No empty interactive elements

---

## 3. FastMCP / AI Client Integration

When using Claude Desktop, Cursor, or Antigravity:
- Register Hath0r CLI connector:
  ```bash
  hath0r mcp serve --install-claude
  ```
- The connector automatically bridges Hath0r's FastMCP server (`hath0r_cli`, `hath0r_design_status`, `hath0r_design_to_code`) and configures `paper-design-mcp`.
