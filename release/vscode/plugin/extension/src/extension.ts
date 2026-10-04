import { ExtensionHath0rClient } from "./client.js";
import { ControlTreeProvider } from "./treeViews/controlTreeProvider.js";
import { AgentsTreeProvider } from "./treeViews/agentsTreeProvider.js";
import { QualityTreeProvider } from "./treeViews/qualityTreeProvider.js";
import { FinOpsTreeProvider } from "./treeViews/finopsTreeProvider.js";
import { registerCommands } from "./commands.js";

export function activate(context: any) {
  let vscode: any;
  try {
    vscode = require("vscode");
  } catch {
    return;
  }

  const workspaceRoot = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || process.cwd();
  const config = vscode.workspace.getConfiguration("hath0r");
  const execPath = config.get("executablePath", "");

  const client = new ExtensionHath0rClient(workspaceRoot, execPath);

  const controlProvider = new ControlTreeProvider(client, vscode);
  const agentsProvider = new AgentsTreeProvider(client, vscode);
  const qualityProvider = new QualityTreeProvider(client, vscode);
  const finopsProvider = new FinOpsTreeProvider(client, vscode);

  vscode.window.registerTreeDataProvider("hath0r-control", controlProvider);
  vscode.window.registerTreeDataProvider("hath0r-agents", agentsProvider);
  vscode.window.registerTreeDataProvider("hath0r-quality", qualityProvider);
  vscode.window.registerTreeDataProvider("hath0r-finops", finopsProvider);

  registerCommands(vscode, context, client, {
    control: controlProvider,
    agents: agentsProvider,
    quality: qualityProvider,
    finops: finopsProvider
  });

  if (config.get("autoPreflightOnStartup", true)) {
    client.runPreflight().then(() => {
      qualityProvider.refresh();
    }).catch(() => {});
  }
}

export function deactivate() {}
