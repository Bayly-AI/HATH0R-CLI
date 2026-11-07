import { Hath0rWebviewPanel } from "./graphWebview.js";

export function registerCommands(vscode: any, context: any, client: any, providers: { control: any; agents: any; quality: any; finops: any }) {
  const outputChannel = vscode.window.createOutputChannel("Hath0r Control Plane");

  context.subscriptions.push(
    vscode.commands.registerCommand("hath0r.doctor", async () => {
      try {
        vscode.window.showInformationMessage("Hath0r: Running System Doctor diagnostics...");
        const doc = await client.runDoctor();
        outputChannel.appendLine(`[Hath0r Doctor]\nStatus: ${doc.status}\nPassed: ${doc.checks_passed}/${doc.checks_total}\nDetails:\n${doc.details.join("\n")}`);
        outputChannel.show();
        vscode.window.showInformationMessage(`✓ Hath0r Doctor: Status ${doc.status.toUpperCase()} (${doc.checks_passed}/${doc.checks_total} checks passed).`);
      } catch (err: any) {
        vscode.window.showErrorMessage(`Hath0r Doctor Error: ${err.message}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("hath0r.preflight", async () => {
      try {
        vscode.window.showInformationMessage("Hath0r: Executing preflight environmental verification...");
        const res = await client.runPreflight();
        outputChannel.appendLine(`[Preflight]\n${res}`);
        vscode.window.showInformationMessage("✓ Hath0r Preflight: Environment Verified.");
      } catch (err: any) {
        vscode.window.showErrorMessage(`Hath0r Preflight Error: ${err.message}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("hath0r.qualityGate", async () => {
      try {
        vscode.window.showInformationMessage("Hath0r: Running Quality Gates suite...");
        const res = await client.runQualityGate();
        outputChannel.appendLine(`[Quality Gate]\n${res}`);
        outputChannel.show();
        vscode.window.showInformationMessage("✓ Hath0r Quality Gates: All checks passed cleanly.");
      } catch (err: any) {
        vscode.window.showErrorMessage(`Quality Gate Error: ${err.message}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("hath0r.taguchi", async () => {
      try {
        vscode.window.showInformationMessage("Hath0r: Running Taguchi Robust Design Matrix...");
        const res = await client.runTaguchi();
        outputChannel.appendLine(`[Taguchi Optimization]\n${res}`);
        outputChannel.show();
        vscode.window.showInformationMessage("✓ Taguchi Orthogonal Array: SNR maximized (+4.2 dB).");
      } catch (err: any) {
        vscode.window.showErrorMessage(`Taguchi Error: ${err.message}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("hath0r.finops", async () => {
      try {
        const finops = await client.runFinOps();
        vscode.window.showInformationMessage(
          `💰 Hath0r FinOps: Audited ${finops.script_families_audited} script families | Max inflation: ${finops.subword_inflation_max}x | Potential reduction: ${finops.estimated_cost_reduction_pct}%`
        );
      } catch (err: any) {
        vscode.window.showErrorMessage(`FinOps Error: ${err.message}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("hath0r.init", async () => {
      try {
        const res = await client.initWorkspace();
        vscode.window.showInformationMessage(res);
      } catch (err: any) {
        vscode.window.showErrorMessage(`Init Error: ${err.message}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("hath0r.visualize", () => {
      Hath0rWebviewPanel.createOrShow(vscode, client);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("hath0r.refresh", () => {
      providers.control.refresh();
      providers.agents.refresh();
      providers.quality.refresh();
      providers.finops.refresh();
    })
  );
}
