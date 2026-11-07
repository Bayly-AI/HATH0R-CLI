export class Hath0rWebviewPanel {
  public static currentPanel: Hath0rWebviewPanel | undefined;
  private readonly panel: any;
  private readonly client: any;

  private constructor(panel: any, client: any) {
    this.panel = panel;
    this.client = client;
    this.update();
    this.panel.onDidDispose(() => this.dispose(), null, []);
  }

  public static createOrShow(vscode: any, client: any) {
    const column = vscode.window.activeTextEditor
      ? vscode.window.activeTextEditor.viewColumn
      : undefined;

    if (Hath0rWebviewPanel.currentPanel) {
      Hath0rWebviewPanel.currentPanel.panel.reveal(column);
      Hath0rWebviewPanel.currentPanel.update();
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "hath0rArchitecture",
      "HATH0R: Enterprise Control Tower",
      column || vscode.ViewColumn.One,
      {
        enableScripts: true,
        retainContextWhenHidden: true
      }
    );

    Hath0rWebviewPanel.currentPanel = new Hath0rWebviewPanel(panel, client);
  }

  public update(): void {
    this.panel.webview.html = this.getHtmlForWebview();
  }

  public dispose() {
    Hath0rWebviewPanel.currentPanel = undefined;
    this.panel.dispose();
  }

  private getHtmlForWebview(): string {
    const mermaidSrc = `
flowchart TD
    subgraph TOWER [Hath0r Autonomous Control Tower]
        OP["Autonomous Operator (CLI)"]
        JEV["JEV Guard (Cryptographic Tool Signing)"]
        DOC["Hath0r Doctor & Preflight Checks"]
    end

    subgraph BOTS [Specialized Autonomous Bots]
        B1["Context Manager Bot"]
        B2["Memory Manager Bot"]
        B3["Token Telemetry Bot"]
        B4["WASM Runtime Sandbox"]
        B5["Voice Daemon (Kokoro)"]
        B6["Paper Design Bot"]
    end

    subgraph SUBSTRATE [Tri-Graph Cognitive Substrate]
        K["KnowledgeGraph (Code & Architecture)"]
        C["ContextGraph (Agent Roles & DAGs)"]
        M["MemoryGraph (Temporal State)"]
    end

    subgraph OPTIMIZE [Optimization & FinOps]
        T1["Taguchi Robust Parameter Optimization"]
        F1["Multilingual Tokenizer Tax Auditor"]
    end

    OP --> JEV
    OP --> DOC
    OP --> BOTS
    BOTS --> SUBSTRATE
    BOTS --> OPTIMIZE
    `;

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>HATH0R Control Plane</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: var(--vscode-editor-background); color: var(--vscode-editor-foreground); padding: 16px; margin: 0; }
    .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--vscode-widget-border); padding-bottom: 12px; margin-bottom: 16px; }
    .title { font-size: 1.2rem; font-weight: 600; color: #8b5cf6; }
    .canvas { background: var(--vscode-editor-background); padding: 20px; border-radius: 8px; border: 1px solid var(--vscode-widget-border); }
  </style>
</head>
<body>
  <div class="header">
    <div class="title">🛰️ HATH0R Enterprise Control Tower & Substrate Architecture</div>
  </div>
  <div class="canvas">
    <pre class="mermaid">${mermaidSrc}</pre>
  </div>
  <script>
    mermaid.initialize({ startOnLoad: true, theme: 'dark' });
  </script>
</body>
</html>`;
  }
}
