/** LSP Client stub — connects to language servers for hover/completion/go-to-definition */
import { executeCommand } from "../shell/index.js";
export interface LSPCapabilities { hover:boolean; completion:boolean; definition:boolean; references:boolean; }
export async function checkLSPAvailable(language: string): Promise<boolean> {
  const serverMap: Record<string,string> = { typescript:"typescript-language-server", python:"pyright", java:"jdtls", go:"gopls", rust:"rust-analyzer" };
  const server = serverMap[language];
  if (!server) return false;
  const r = await executeCommand({ command:`${server} --version 2>&1` });
  return !r.isError;
}
export function getLSPCapabilities(): LSPCapabilities {
  return { hover:false, completion:false, definition:false, references:false };
}
